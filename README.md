# Theorist Toolbox

A small set of Claude Code *skills* for doing economic theory with LLMs — proving
results, checking them, and running a whole proof-building project the way you'd run
a research team.

Empirical economists have had shared tooling for years. The empiricist learns the
craft from reusable, opinionated tools. Theorists rarely really got that. This is an
attempt at the theory-side equivalent: a toolkit that encodes *how* to push an LLM
through a proof without letting it hand-wave.

The three skills are three different bets on the same problem — *how do you get
machine help on a theorem you don't already know how to prove, and trust the answer?*

## The skills

| Skill | The bet | What it is |
|-------|---------|-----------|
| **`math-proof`** | One careful pass. | A discipline for writing a full, gap-free proof in a single shot: state what you'll show before showing it, sign every term, no "clearly," no overgeneralizing from examples. |
| **`codex-math`** | Two minds, one adversarial. | Drives OpenAI Codex (gpt-5.5) as a *co-processor and hostile verifier* — propose, then try to break, then triage. Built around the rule that Codex is a brilliant, unreliable mathematician: every output is a lead, not a verdict. |
| **`co-math-init` / `co-math-status`** | A research team, not a chat. | Scaffolds a structured proof-building *project* — `paper.tex`, goals, decisions log, workstreams, strict mode where every gap is flagged `\unproven{}` and nothing is "complete" without a reviewer's sign-off. The architecture follows Zheng et al. (2026), *AI co-mathematician* (Google DeepMind). `co-math-status` renders the project state. |

Each is a different point on a trade-off between speed, verification, and coverage:
the single pass is fastest and cleanest but unchecked; the adversarial pair is the
most reliable per claim; the structured team gives the broadest, most disciplined
coverage and can *reject its own work*.

## The case study (`examples/`)

I built these while testing all three on one problem: turning the *eigengrade* of
Gans & Kominers (2026, *"What Does a Grade Mean?"*, NBER w35183) into a VCG-style
mechanism against grade inflation. Each skill produced a self-contained writeup:

- `1-math-proover_…` — a student-side enrollment VCG (single pass, `math-proof`).
- `2-codex-proover_…` — an instructor-side Pigouvian/Groves transfer, adversarially
  verified with Codex + Monte Carlo (`codex-math`).
- `3-co-math_…` — a money-free, report-space mechanism *suite* with an impossibility
  theorem and a numerically validated running example (`co-math`).

Two of the three independently rediscovered the same externality kernel; the third's
reviewer gate killed one of its own sub-goals. The write-up of that comparison lives
in the accompanying Substack post.

## Install

These are Claude Code skills. Drop the folders into your skills directory:

```bash
cp -R skills/* ~/.claude/skills/
```

Then invoke them from Claude Code (`/math-proof`, `/co-math-init`, …) or let the model
pick them up by description.

### Notes

- **`codex-math`** documents the *interface* to a set of companion runner scripts
  (`codex_verify.sh`, `codex_write.sh`, `codex_explore.sh`) that wrap the
  [OpenAI Codex CLI](https://github.com/openai/codex). Those live alongside your
  project (`code/utils/codex_math/`) and call `codex exec`; you'll need the Codex CLI
  installed and authenticated. The skill is the playbook for using it well.
- **`co-math-init`** writes per-project hooks that reference
  `~/.claude/co-math/hooks/` (a `paper_tex_guard.py` and a
  `workstream_complete_guard.py` that enforce strict mode). Provide your own, or run
  with the guards disabled — the skill works either way; the hooks are the teeth.

## Author

Moran Koren, Ben-Gurion University of the Negev — korenmor@bgu.ac.il.
If you use the toolbox in research, a mention is appreciated.

## License

MIT. See `LICENSE`. Use them, fork them, tell me what broke.
