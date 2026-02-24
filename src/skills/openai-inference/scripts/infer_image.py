#!/usr/bin/env python3
"""Run image inference through OpenAI Responses API (compatibility wrapper)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from infer import run_inference


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Path to local image file")
    parser.add_argument("--prompt", required=True, help="Task prompt sent with the image")
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
    parser.add_argument(
        "--action-taken",
        default="",
        help="Optional action taken from the inference result for audit logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"image file not found: {image_path}")

    result = run_inference(prompt=args.prompt, model=args.model, image_path=image_path, web_search=False)
    if args.action_taken.strip():
        result["action_taken"] = args.action_taken.strip()
    if "confidence" not in result:
        result["confidence"] = None
    if "inference_output" not in result:
        result["inference_output"] = str(result.get("output_text", ""))
    rendered = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)


if __name__ == "__main__":
    main()
