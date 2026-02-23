# User Skills

Add custom skills in this directory using:

- `skills/<skill-name>/SKILL.md`

Runtime precedence is:

1. `skills/<skill-name>/SKILL.md` (user)
2. `src/skills/<skill-name>/SKILL.md` (bundled)

If both exist with the same `name`, the user skill wins.

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
