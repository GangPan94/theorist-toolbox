---
name: co-math-init
description: Initialize a disciplined AI co-mathematician research project for Codex. Use when starting a math or economic theory investigation that needs goals.md, paper.tex, workstreams, decisions, reviewer approvals, strict no-hand-waving proof tracking, Lean/code workstreams, or a durable co-math project scaffold.
---

# Co-Math Init

Create a local research project modeled on the Theorist Toolbox co-math workflow. The project keeps a living `paper.tex`, explicit goals, append-only decisions, workstream reports, reviewer approvals, failed explorations, and open proof obligations.

Strict mode is the default. In strict mode, every proof gap must be marked with `\unproven{...}` until reviewed or machine-checked.

## Inputs

Gather or infer:

- project name: lowercase kebab-case,
- research question: one or two sentences,
- parent directory: default to the current working directory,
- strict mode: default `true`; only set `false` if the user explicitly asks for pragmatic mode.

If the project name is missing, derive a short kebab-case name from the research question. If the research question is missing, ask for it.

## Create The Project

Run the bundled script from the skill directory:

```bash
python3 scripts/init_co_math_project.py \
  --name <project-name> \
  --question "<research question>" \
  --parent <parent-directory>
```

For pragmatic mode:

```bash
python3 scripts/init_co_math_project.py \
  --name <project-name> \
  --question "<research question>" \
  --parent <parent-directory> \
  --pragmatic
```

The script creates:

```text
paper.tex
goals.md
decisions.md
README.md
AGENTS.md
co-math-config.json
workstreams/.gitkeep
references/.gitkeep
failed-explorations/.gitkeep
.co-math/approvals/.gitkeep
.co-math/workstream-registry.json
```

## After Initialization

Tell the user:

- the absolute path of the created project,
- `goals.md` is where the research question and sub-goals are refined,
- no workstream should start until goals are approved,
- `paper.tex` is the living paper,
- `workstreams/` will hold one directory per proof, literature, code, Lean, or readability task,
- `.co-math/approvals/` is the reviewer gate,
- `failed-explorations/` is intentionally durable and should not be cleaned away.

If the package's Codex custom agents are installed, suggest starting with the `co-math-project-coordinator` agent. If not, Codex can still run the workflow manually using the project files and the role profiles in this package.

## What Not To Do

- Do not start proving immediately during initialization.
- Do not mark goals approved on behalf of the user.
- Do not disable strict mode unless the user explicitly asks.
- Do not remove `\unproven{}` obligations to make the paper look cleaner.
