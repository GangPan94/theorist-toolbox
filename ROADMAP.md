# Roadmap

This is the maintainer's view of where the Theorist Toolbox is headed. It is a
direction, not a contract — and it is discussed in the open. To weigh in, comment on
the pinned **[RFC] Roadmap** issue or open a [Discussion](../../discussions).

## The vision

A shared, opinionated toolkit that lets an economic theorist get *trustworthy*
machine help on a proof — from a single careful pass, to an adversarial verifier, to
a full research-team workflow that can reject its own work. The invariant across
everything we add: **the tool makes the model more correct, never just more
confident.**

The core stays small. Growth happens at the edges, as modules:

- **skills** — disciplines the model follows (proving, checking, writing).
- **agents** — co-math sub-agents with a job, tools, and an honest failure mode.
- **case studies** — worked, reproducible examples that show the discipline holding
  (or honestly failing).

## Candidate next modules

These are proposals, ranked by how often they'd pay off. Pick one up, or argue for a
different ordering in the RFC.

1. **Boundary-condition / edge-case skill.** A discipline that forces the model to
   enumerate degenerate cases (empty type space, ties, corner solutions, measure-zero
   events) before declaring a proof complete — the single most common gap in
   theory proofs.
2. **Extensive-form / game-tree reasoning skill.** Structured handling of subgame
   perfection, information sets, and backward induction, where LLMs currently flail.
3. **Counterexample-search agent.** A sibling to `coder` whose job is purely
   adversarial: given a conjecture, search numerically/symbolically for a refutation
   before any proof effort is spent.
4. **Referee-response skill.** Drafts point-by-point responses to referee reports
   with the same justification discipline the proofs use — a natural bridge to the
   `academic-writing` side of a theorist's workflow.
5. **Wider Lean coverage.** Helpers that map common econ-theory constructs (preference
   relations, fixed-point arguments, measure-theoretic limits) onto mathlib, lowering
   the cost of a `lean-prover` workstream.

## Out of scope (for now)

- Heavy governance machinery (CLAs, SLAs, multi-track review). Right-sized for the
  community we have, not the one a roadmap fantasises about.
- Provider lock-in. Skills should encode discipline, not hard-code one model's quirks.

## How priorities get set

The maintainer sets direction (the BDFL role), but the ordering above is exactly what
the RFC is for. A module with a contributor willing to own it beats a "nice to have"
with nobody behind it — if you want to build one of these, say so and it moves up.
