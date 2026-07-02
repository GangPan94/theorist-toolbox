# Theorist Toolbox Reference For ChatGPT

This file summarizes the OpenAI-compatible adaptation of Moran Koren's Theorist Toolbox.

## Workflows

### Math Proof

Use for proving results, deriving equations, justifying analytical claims, and expanding proof sketches. Output a complete proof with setup, numbered steps, explicit algebra, sign checks, edge cases, and intuition.

Failure condition: if the proof cannot be closed, state the exact unresolved obligation and the strongest result established.

### Adversarial Math

Use for independent verification, counterexample search, hard proof attempts, and conjecture exploration.

Modes:

- verify: classify proof steps as `OK`, `GAP`, `ERROR`, or `UNCLEAR`;
- write: propose a proof, then self-audit it;
- explore: search for counterexamples, sufficient conditions, and weaker true statements.

### Co-Math

Use for research projects too large for one proof response. Maintain:

- goals,
- decisions,
- workstreams,
- reports,
- reviewer approvals,
- failed explorations,
- open proof obligations.

Workstream roles:

- project coordinator: refines goals, dispatches work, summarizes state;
- literature reviewer: verifies sources and writes citation notes;
- prover: writes proofs with explicit open obligations;
- coder: runs computational exploration with tests and golden values;
- Lean prover: formalizes important lemmas in Lean 4 when possible;
- paper reviewer: adversarial gate before anything is complete.

### Proof Readability

Use only after correctness is accepted. It improves exposition while preserving the argument.

Six layers:

1. architecture,
2. signposting,
3. line-level justification,
4. notation hygiene,
5. intuition,
6. sentence and formula grammar.

## Hard Rules

- Do not hand-wave.
- Do not invent citations.
- Do not treat examples as proof.
- Do not erase failed attempts.
- Do not change mathematical content during readability edits.
- Do not claim review approval unless a review was actually performed.
