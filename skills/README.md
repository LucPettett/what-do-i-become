# User Skills

Add custom skills in this directory using:

- `skills/<skill-name>/SKILL.md`

Runtime precedence is:

1. `skills/<skill-name>/SKILL.md` (user)
2. `src/skills/<skill-name>/SKILL.md` (bundled)

If both exist with the same `name`, the user skill wins.

## Spirit vs Skills contract

Skills are capability playbooks, not mission statements.

- A skill must define `how` to execute work:
  - prerequisites
  - steps/commands
  - expected outputs and verification checks
- A skill must not define `what the device should become`.
- A skill must not override Spirit safety boundaries or escalation policy.

If a task conflicts with `SPIRIT.md`, update the skill or skip it. Do not violate Spirit constraints.

## Minimal template

```markdown
---
name: my-skill
description: One-line purpose.
metadata:
  requires:
    bins: [python3]
    env: []
  os: [linux, darwin]
---

# my-skill

Describe the workflow the agent should follow.
```
