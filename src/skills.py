#!/usr/bin/env python3
"""Skill discovery and prompt shaping for what-do-i-become."""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FRAMEWORK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRAMEWORK_DIR.parent
SOURCE_PRIORITY = {"bundled": 0, "workspace": 1}


@dataclass
class SkillCandidate:
    name: str
    description: str
    source: str
    directory: Path
    file_path: Path
    instructions: str
    metadata: dict[str, Any]
    priority: int


def _parse_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        text = str(raw).strip()
        if not text:
            return []
        normalized = text.replace(";", ",").replace(os.pathsep, ",")
        values = [part.strip() for part in normalized.split(",")]
    return [item for item in values if item]


def _split_front_matter(content: str) -> tuple[dict[str, Any], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    end_index = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index < 0:
        return {}, content

    front_matter_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    try:
        parsed = yaml.safe_load(front_matter_text) or {}
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}

    return parsed, body


def _normalize_skill_name(name: Any, fallback: str) -> str:
    raw = str(name or fallback).strip().lower().replace(" ", "-")
    kept: list[str] = []
    for char in raw:
        if char.isalnum() or char in {"-", "_"}:
            kept.append(char)
    normalized = "".join(kept).strip("-_")
    return normalized or fallback.lower()


def _extract_metadata(front_matter: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    raw_metadata = front_matter.get("metadata")
    if isinstance(raw_metadata, dict):
        metadata.update(raw_metadata)

    if "requires" in front_matter and "requires" not in metadata:
        requires = front_matter.get("requires")
        if isinstance(requires, dict):
            metadata["requires"] = requires

    if "os" in front_matter and "os" not in metadata:
        metadata["os"] = front_matter.get("os")

    return metadata


def _path_to_display(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _skill_matches_runtime(candidate: SkillCandidate) -> tuple[bool, str]:
    metadata = candidate.metadata
    requires = metadata.get("requires")
    if not isinstance(requires, dict):
        requires = {}

    missing_bins = [binary for binary in _parse_list(requires.get("bins")) if shutil.which(binary) is None]
    if missing_bins:
        return False, f"missing required binaries: {', '.join(missing_bins)}"

    missing_env = [key for key in _parse_list(requires.get("env")) if not os.environ.get(key)]
    if missing_env:
        return False, f"missing required env vars: {', '.join(missing_env)}"

    allowed_os = [item.lower() for item in _parse_list(metadata.get("os"))]
    if allowed_os:
        current_os = platform.system().lower()
        if current_os not in allowed_os:
            return False, f"unsupported OS: {current_os} (allowed: {', '.join(allowed_os)})"

    return True, ""


def _iter_source_dirs() -> list[tuple[str, Path]]:
    return [
        ("bundled", FRAMEWORK_DIR / "skills"),
        ("workspace", PROJECT_ROOT / "skills"),
    ]


def _read_skill_file(source: str, skill_file: Path) -> SkillCandidate | None:
    try:
        raw = skill_file.read_text(encoding="utf-8")
    except OSError:
        return None

    front_matter, body = _split_front_matter(raw)
    fallback_name = skill_file.parent.name
    name = _normalize_skill_name(front_matter.get("name"), fallback=fallback_name)
    description = str(front_matter.get("description") or "").strip()
    instructions = body.strip() if body.strip() else raw.strip()
    metadata = _extract_metadata(front_matter)
    priority = SOURCE_PRIORITY.get(source, 0)

    return SkillCandidate(
        name=name,
        description=description,
        source=source,
        directory=skill_file.parent,
        file_path=skill_file,
        instructions=instructions,
        metadata=metadata,
        priority=priority,
    )


def _discover_candidates() -> list[SkillCandidate]:
    discovered: list[SkillCandidate] = []
    for source, root in _iter_source_dirs():
        if not root.exists() or not root.is_dir():
            continue
        for skill_file in sorted(root.glob("*/SKILL.md")):
            candidate = _read_skill_file(source, skill_file)
            if candidate:
                discovered.append(candidate)
    return discovered


def _select_skills(candidates: list[SkillCandidate]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    grouped: dict[str, list[SkillCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.name, []).append(candidate)

    available: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for skill_name in sorted(grouped):
        ranked = sorted(grouped[skill_name], key=lambda item: item.priority, reverse=True)
        selected: SkillCandidate | None = None

        for candidate in ranked:
            eligible, ineligible_reason = _skill_matches_runtime(candidate)
            if not eligible:
                skipped.append(
                    {
                        "name": candidate.name,
                        "source": candidate.source,
                        "path": _path_to_display(candidate.file_path),
                        "reason": ineligible_reason,
                    }
                )
                continue

            selected = candidate
            break

        if not selected:
            continue

        available.append(
            {
                "name": selected.name,
                "description": selected.description,
                "source": selected.source,
                "directory": _path_to_display(selected.directory),
                "skill_file": _path_to_display(selected.file_path),
                "instructions": selected.instructions,
                "metadata": selected.metadata,
            }
        )

    return available, skipped


def load_skill_snapshot() -> dict[str, Any]:
    candidates = _discover_candidates()
    available, skipped = _select_skills(candidates)
    return {
        "available": available,
        "skipped": skipped,
    }


def _trim(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n[TRUNCATED]"


def render_skill_prompt_block(
    snapshot: dict[str, Any],
    *,
    max_skill_instructions: int = 1400,
    max_skill_count: int = 8,
) -> str:
    skills = snapshot.get("available") or []
    if not skills:
        return """
== SKILLS ==
No eligible skills loaded this session.
"""

    lines = [
        "== SKILLS ==",
        "Use skills as reusable playbooks when a task matches their purpose.",
        "Available skills (highest-precedence eligible version selected):",
    ]

    for idx, skill in enumerate(skills, 1):
        description = str(skill.get("description") or "").strip() or "(no description)"
        lines.append(
            f"  {idx}. {skill.get('name')} [{skill.get('source')}] - {description} "
            f"(path: {skill.get('directory')})"
        )

    lines.append("")
    lines.append("== SKILL PLAYBOOKS ==")

    for skill in skills[:max_skill_count]:
        lines.append("")
        lines.append(f"--- {skill.get('name')} ---")
        lines.append(_trim(str(skill.get("instructions") or ""), max_skill_instructions))

    return "\n".join(lines)
