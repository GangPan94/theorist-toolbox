#!/usr/bin/env python3
"""Initialize a Codex-flavored co-math research project."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Project name in kebab-case.")
    parser.add_argument("--question", required=True, help="Initial research question.")
    parser.add_argument("--parent", default=".", help="Parent directory. Defaults to cwd.")
    parser.add_argument(
        "--pragmatic",
        action="store_true",
        help="Disable strict mode for this project. Strict mode is the default.",
    )
    return parser.parse_args()


def validate_name(name: str) -> None:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name):
        raise SystemExit(
            "Project name must be kebab-case: lowercase letters, digits, and hyphens."
        )


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


PROJECT_README = """# {{PROJECT_NAME}}

Codex co-mathematician research project.
Initialized {{DATE}}.

## Research question

{{RESEARCH_QUESTION}}

See `goals.md` for the full goal structure and approval status.

## Layout

| Path | Purpose |
|---|---|
| `paper.tex` | Living working paper. |
| `goals.md` | Research question, sub-goals, approval status. |
| `decisions.md` | Append-only decision log. |
| `co-math-config.json` | Per-project settings. |
| `workstreams/` | One directory per literature, proof, code, Lean, review, or readability task. |
| `references/` | Verified citation notes and source material. |
| `failed-explorations/` | Durable record of approaches that failed. |
| `.co-math/approvals/` | Reviewer approval files. |

## Working discipline

1. Refine `goals.md` until the research question, sub-goals, out-of-scope items, and success criteria are clear.
2. Do not spawn workstreams until `goals.md` says `Goals approved by user: YES`.
3. Keep every workstream self-contained: `instructions.md`, `status.md`, `log.md`, and `report.md`.
4. A workstream is not complete until a reviewer writes an approval file under `.co-math/approvals/`.
5. In strict mode, every proof gap in `paper.tex` is marked with `\\unproven{...}`.
6. Preserve failed explorations. They are negative evidence, not clutter.
"""


AGENTS_MD = """# Co-Math Project Instructions

This repository is a Codex co-mathematician project generated from the OpenAI-compatible Theorist Toolbox.

## Core Rules

- Treat the user as the research lead.
- Keep `goals.md` as the source of truth for project intent.
- Do not start workstreams before user approval is recorded in `goals.md`.
- Every workstream lives under `workstreams/W{NNN}-{slug}/` and contains `instructions.md`, `status.md`, `log.md`, and `report.md`.
- Never mark a workstream complete without an approval file in `.co-math/approvals/`.
- In strict mode, every proof step is justified, cited, or explicitly marked `\\unproven{...}`.
- Do not remove failed explorations. Move abandoned attempts to `failed-explorations/` with a summary of what was learned.

## Role Map

Use these roles when the user asks for subagents or role-based work:

- `co-math-project-coordinator`: refine goals, dispatch workstreams, summarize status.
- `co-math-literature-reviewer`: verify literature and write citation notes.
- `co-math-prover`: draft rigorous proofs and flag gaps.
- `co-math-coder`: computational exploration with tests and golden values.
- `co-math-lean-prover`: Lean 4 formalization with `lake build`.
- `co-math-paper-reviewer`: adversarial approval gate.

If custom agents are not installed, follow the same role instructions manually.
"""


GOALS_MD = """# Goals - {{PROJECT_NAME}}

Initialized {{DATE}}.

## Research question

{{RESEARCH_QUESTION}}

## Sub-goals

_The project coordinator should propose sub-goals after an initial dialogue. The user must approve them before any workstream starts._

## Out of scope

_List tempting directions the project should not pursue._

## Success criteria

_What counts as done? A theorem statement, a bound, a verified counterexample, a literature map, or a paper section._

## Approval

Goals approved by user: **NO**
"""


DECISIONS_MD = """# Decisions log - {{PROJECT_NAME}}

Append-only. Most recent entries should go near the top.

---

## {{DATE}} - Project initialized

- Research question recorded in `goals.md`.
- Strict mode: `{{STRICT_MODE_WORD}}`.
- No workstreams yet.
- Goals are not approved. No workstream should start until `goals.md` records approval.
"""


CONFIG_JSON = {
    "paper_format": "latex",
    "review_policy": {
        "require_reviewer_approval_for_complete": True,
        "require_citation_validation": True,
        "block_theorem_without_proof_or_unproven": True,
        "lean_accepted_in_lieu_of_proof": True,
        "readability_pass_after_approval": True,
    },
    "workstream_naming": "W{NNN}-{slug}",
    "codex_agents": {
        "project_coordinator": "co-math-project-coordinator",
        "literature_reviewer": "co-math-literature-reviewer",
        "prover": "co-math-prover",
        "coder": "co-math-coder",
        "lean_prover": "co-math-lean-prover",
        "paper_reviewer": "co-math-paper-reviewer",
    },
}


PAPER_TEX = r"""\documentclass[11pt]{article}

% Codex co-mathematician working paper
% Project: {{PROJECT_NAME}}
% Initialized: {{DATE}}

\usepackage[a4paper,margin=1in,marginparwidth=1.4in,marginparsep=0.2in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{mathtools}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{marginnote}
\usepackage{enumitem}
\usepackage{etoolbox}

\hypersetup{
  colorlinks=true,
  linkcolor=blue!50!black,
  citecolor=blue!50!black,
  urlcolor=blue!50!black
}

\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{example}[theorem]{Example}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}

\newcounter{unprovencount}
\newcommand{\unprovenlist}{}

\newcommand{\unproven}[1]{%
  \stepcounter{unprovencount}%
  \textcolor{red!80!black}{\textbf{[UNPROVEN \theunprovencount]} #1}%
  \marginnote{\footnotesize\textcolor{red!80!black}{unproven \#\theunprovencount}}%
  \xappto\unprovenlist{\item[\textbf{\#\theunprovencount}] #1\par}%
}

\newcommand{\marginorigin}[1]{\marginnote{\footnotesize\textit{origin:} #1}}
\newcommand{\internalref}[2]{\href{run:#1}{\texttt{#2}}}
\newcommand{\claim}[1]{\textit{#1}\marginnote{\footnotesize\textcolor{orange!70!black}{claim - needs justification}}}
\newcommand{\leanproved}[1]{%
  \textcolor{green!50!black}{$\blacksquare$ \textit{Lean-verified in }\internalref{workstreams/#1/lean/Main.lean}{\texttt{#1}}\textit{.}}%
  \marginnote{\footnotesize\textcolor{green!50!black}{Lean: #1}}%
}

\title{ {{PROJECT_NAME}} \\ \large Working paper }
\author{}
\date{Initialized {{DATE}}}

\begin{document}
\maketitle

\begin{abstract}
\textit{Working draft.} Research question: {{RESEARCH_QUESTION}}

\medskip
This is a living document maintained through a co-mathematician workflow.
Margin notes record provenance. Open proof obligations are marked with the
\texttt{\textbackslash{}unproven} macro and collected in the appendix.
\end{abstract}

\tableofcontents

\section{Introduction}

\marginorigin{co-math-init}
This section will be drafted after the user approves the goals in
\internalref{goals.md}{goals.md}.

\section{Preliminaries}

\textit{To be drafted by literature-reviewer workstreams.}

\section{Main results}

\textit{To be drafted by prover workstreams.}

\section{Computational evidence}

\textit{To be drafted by coder workstreams.}

\section{Discussion}

\textit{To be drafted after the main results stabilize.}

\appendix

\section{Open obligations}
\label{app:open}

\begin{description}
\unprovenlist
\end{description}

\section{Failed explorations}

Summaries of abandoned approaches live in
\internalref{failed-explorations/}{failed-explorations/}.

\end{document}
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    validate_name(args.name)

    parent = Path(args.parent).expanduser().resolve()
    project = parent / args.name
    if project.exists() and any(project.iterdir()):
        raise SystemExit(f"Refusing to initialize non-empty directory: {project}")

    today = date.today().isoformat()
    strict_mode = not args.pragmatic
    values = {
        "PROJECT_NAME": args.name,
        "RESEARCH_QUESTION": args.question,
        "DATE": today,
        "STRICT_MODE": "true" if strict_mode else "false",
        "STRICT_MODE_WORD": "strict" if strict_mode else "pragmatic",
    }

    for directory in [
        "workstreams",
        "references",
        "failed-explorations",
        ".co-math/approvals",
    ]:
        (project / directory).mkdir(parents=True, exist_ok=True)
        write_text(project / directory / ".gitkeep", "")

    write_text(project / "README.md", render(PROJECT_README, values))
    write_text(project / "AGENTS.md", render(AGENTS_MD, values))
    write_text(project / "goals.md", render(GOALS_MD, values))
    write_text(project / "decisions.md", render(DECISIONS_MD, values))
    write_text(project / "paper.tex", render(PAPER_TEX, values))

    config = dict(CONFIG_JSON)
    config.update(
        {
            "project": args.name,
            "created": today,
            "strict_mode": strict_mode,
        }
    )
    write_text(project / "co-math-config.json", json.dumps(config, indent=2) + "\n")

    registry = {
        "project": args.name,
        "created": today,
        "strict_mode": strict_mode,
        "next_id": 1,
        "workstreams": [],
    }
    write_text(
        project / ".co-math" / "workstream-registry.json",
        json.dumps(registry, indent=2) + "\n",
    )

    print(f"Created co-math project: {project}")
    print("Next: refine goals.md and set approval to YES before starting workstreams.")


if __name__ == "__main__":
    main()
