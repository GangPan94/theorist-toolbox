---
name: co-math-status
description: Render a compact status view for a Codex co-mathematician project. Use when the user asks for project status, active workstreams, blocked items, pending reviews, open proof obligations, recent decisions, or "what is happening in this co-math project".
---

# Co-Math Status

Summarize the state of a co-math research project without making changes.

## Workflow

1. Start from the current directory unless the user gives a project path.
2. Run the bundled script:

```bash
python3 scripts/render_co_math_status.py <optional-project-or-child-path>
```

3. Show the rendered status.
4. Add a short human summary: running workstreams, blocked workstreams, pending reviews, and the most important next action.

The script walks upward until it finds `co-math-config.json`. If it cannot find one, say that the current directory is not inside a co-math project.

## Do More Only On Request

If the user asks to inspect a specific workstream, read that workstream's `instructions.md`, `status.md`, `log.md`, and `report.md`, then summarize the relevant parts. Do not dump long logs unless asked.
