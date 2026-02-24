---
name: openai-inference
description: Run OpenAI inference for text, image analysis, and web lookup.
metadata:
  requires:
    bins:
      - python3
    env:
      - OPENAI_API_KEY
  os:
    - linux
    - darwin
---

# openai-inference

Use this skill when you need model-based reasoning from text questions, camera frames, or web-grounded lookups.

## Outcomes
- Ask general questions through the model.
- Run image understanding from local files.
- Run web lookup with model synthesis.
- Produce machine-readable JSON results when needed for planning.
- Save inference evidence in device artifacts for cross-wake continuity.

## Script

- `scripts/infer.py` (primary)
- `scripts/infer_image.py` (image-only compatibility wrapper)

## Standard workflow

1. Choose inference mode: text-only, text+image, or text+web lookup.
2. Write a strict task prompt; request JSON when the output must drive automation.
3. Run `infer.py` with optional `--image` and `--web-search`.
4. Save output JSON under your device directory for auditability.
5. Use the returned output and confidence fields to decide the next action.
6. Call `log_inference_artifact` with `input_images`, `inference_output`, `confidence`, and `action_taken`.

## Command templates

```bash
python3 src/skills/openai-inference/scripts/infer.py \
  --prompt "What are three likely causes of intermittent wheel encoder drops?" \
  --output devices/<uuid>/artifacts/inference/question.json
```

```bash
python3 src/skills/openai-inference/scripts/infer.py \
  --image devices/<uuid>/artifacts/latest.jpg \
  --prompt "Return JSON with keys: objects, confidence, next_action. Detect rubbish-like items." \
  --expect-json \
  --output devices/<uuid>/artifacts/inference/image.json
```

```bash
python3 src/skills/openai-inference/scripts/infer.py \
  --prompt "Find recent local guidance on beach litter collection zones and return JSON with links." \
  --web-search \
  --expect-json \
  --output devices/<uuid>/artifacts/inference/web.json
```

## Reliability notes

- If `OPENAI_API_KEY` is missing, do not proceed; request operator action.
- Keep prompts explicit about output shape, confidence thresholds, and required keys.
- Use `--expect-json` for machine-consumable outputs; if parsing fails, treat as an incident.
- Store the raw inference text plus parsed JSON so retries can recover.
- Never leave an inference decision unlogged; persist it as an inference artifact.
