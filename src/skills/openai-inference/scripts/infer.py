#!/usr/bin/env python3
"""Run OpenAI inference for text, image, and optional web lookup."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Task prompt sent to the model")
    parser.add_argument("--image", default="", help="Optional local image path")
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable web search tool for web-grounded answers.",
    )
    parser.add_argument(
        "--expect-json",
        action="store_true",
        help="Attempt to parse output_text as JSON and report parse status.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WDIB_INFERENCE_MODEL")
        or os.environ.get("WDIB_LLM_MODEL")
        or "gpt-5",
        help="OpenAI model for inference",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output path. If omitted, JSON is printed to stdout only.",
    )
    return parser.parse_args()


def encode_image(image_path: Path) -> tuple[str, str]:
    guessed_mime, _ = mimetypes.guess_type(str(image_path))
    mime = guessed_mime or "image/jpeg"
    payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return mime, payload


def _extract_tool_calls(response: Any) -> list[str]:
    tool_calls: list[str] = []
    for item in getattr(response, "output", []) or []:
        item_type = getattr(item, "type", None)
        if item_type and item_type.endswith("_call"):
            tool_calls.append(str(item_type))
    return sorted(set(tool_calls))


def run_inference(
    *,
    prompt: str,
    model: str,
    image_path: Path | None = None,
    web_search: bool = False,
) -> dict[str, object]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    from openai import OpenAI

    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    image_path_text = ""

    if image_path is not None:
        mime_type, image_b64 = encode_image(image_path)
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{image_b64}",
            }
        )
        image_path_text = str(image_path)

    request_payload: dict[str, Any] = {
        "model": model,
        "input": [{"role": "user", "content": content}],
    }
    if web_search:
        request_payload["tools"] = [{"type": "web_search_preview"}]

    client = OpenAI()
    response = client.responses.create(**request_payload)

    output_text = (getattr(response, "output_text", "") or "").strip()
    tool_calls = _extract_tool_calls(response)

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "prompt": prompt,
        "image_path": image_path_text,
        "web_search": web_search,
        "response_id": getattr(response, "id", None),
        "tool_calls": tool_calls,
        "output_text": output_text,
    }


def main() -> None:
    args = parse_args()

    image_path: Path | None = None
    if args.image:
        resolved_image = Path(args.image).expanduser().resolve()
        if not resolved_image.exists():
            raise FileNotFoundError(f"image file not found: {resolved_image}")
        image_path = resolved_image

    result = run_inference(
        prompt=args.prompt,
        model=args.model,
        image_path=image_path,
        web_search=args.web_search,
    )

    if args.expect_json:
        parsed_json: Any | None = None
        parse_error = ""
        try:
            parsed_json = json.loads(str(result.get("output_text", "")))
        except json.JSONDecodeError as exc:
            parse_error = str(exc)

        result["json_valid"] = bool(parse_error == "")
        result["json_error"] = parse_error
        if parsed_json is not None:
            result["parsed_json"] = parsed_json

    rendered = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)


if __name__ == "__main__":
    main()
