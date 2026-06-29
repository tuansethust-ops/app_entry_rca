# Cline Skill Format

Every project skill is discoverable from `.cline/skills/<skill-name>/SKILL.md`.

```markdown
---
name: <skill-name>
description: What the skill does and when Cline should use it.
---

# Skill title

## Purpose
## Trigger
## Required input
## Workflow
## Algorithm contract
## Main outputs
## Leaf and workflow integration
## Guardrails
## Failure handling
## Known limitation
## Implementation
## Tests
```

Rules:

1. `name` must exactly match the directory name.
2. Use lowercase kebab-case names.
3. `description` must explain both capability and trigger context.
4. The `.cline/skills` copy and canonical `skills` copy must stay identical.
5. A skill describes one reusable capability; the top-level workflow owns ordering and routing.
