---
name: coding-ops
description: Write, run, and debug software using shell commands and file edits.
metadata:
  requires:
    bins:
      - python3
      - git
  os:
    - linux
    - darwin
---

# coding-ops

Use this skill for software implementation and OS navigation tasks.

## Scope
- Write and edit code files.
- Navigate the filesystem and inspect runtime state.
- Run bash commands and read outputs.
- Verify behavior with tests or executable checks.
- Debug failures and produce concrete follow-up actions.

## Workflow

1. Define the exact behavior change and acceptance check.
2. Discover the right files with fast search (`rg --files`, `rg <pattern>`).
3. Make minimal edits that are easy to validate.
4. Run verification commands immediately after edits.
5. If checks fail, patch and rerun in the same wake when possible.
6. Save evidence (command outputs, changed files, remaining issues).

## Command patterns

```bash
rg --files
rg "target_symbol|target_phrase" src
python3 -m py_compile src/*.py
```

## Reliability rules

- Prefer deterministic commands and explicit working directories.
- Keep edits small and verifiable.
- Treat failed checks as incidents: capture the exact command and error text.
- Avoid introducing new dependencies unless required for the task.
