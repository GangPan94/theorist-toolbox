---
name: math-proof
description: Write rigorous, gap-free mathematical proofs for academic research. Use when asked to prove, derive, justify analytically, expand a proof sketch, check a theorem statement, or turn economic or game-theoretic reasoning into a complete proof with explicit algebra, signs, edge cases, and no hand-waving.
---

# Math Proof

Write proofs suitable for a paper draft. The deliverable is a complete proof, not an outline. Every transition must be checkable by a skeptical reader without filling in missing algebra, sign arguments, or quantifier choices.

This skill adapts Moran Koren's Theorist Toolbox proof discipline for Codex. Preserve the core invariant: if a step is not proved, cited, or explicitly marked as conjectural, do not present it as established.

## Workflow

1. Parse the exact claim, hypotheses, domains, and conclusion.
2. State the proof plan before proving: direct proof, contradiction, induction, fixed point, comparative statics, counterexample search, or case split.
3. Define all notation before use. Give object types and parameter domains.
4. Prove one numbered step at a time. Each step must open with what it will show.
5. Show intermediate algebra. Do not jump from setup to simplified result.
6. Sign every derivative, inequality, monotonicity claim, and limit claim at the line where it appears.
7. Handle edge cases and boundary behavior explicitly.
8. Separate proved results from conjectures, examples, and numerical evidence.
9. End with a short intuition paragraph when useful, then close the proof with `\square`.

## Proof Discipline

- Use `\triangleq` for definitions and `=` for equalities.
- Use display math for multi-term expressions, ratios, derivatives, thresholds, and relation chains.
- Before algebra, say the goal: "It remains to show that ...".
- When differentiating a ratio, compute numerator and denominator derivatives before applying the quotient rule.
- When manipulating inequalities, state why the inequality direction is preserved or reversed.
- If a threshold is integer-valued but differentiated as continuous, flag the relaxation and explain how discreteness affects the claim.
- When invoking a theorem, instantiate it in the paper's notation. If the theorem is not standard, cite it precisely or prove the needed lemma.
- Never prove the general case by checking examples. Examples are evidence, not proof.

## Banned Moves

Do not use these phrases or their equivalents unless immediately followed by the missing argument:

- clearly
- obviously
- it is easy to see
- straightforward
- by a similar argument
- omitted for brevity
- this dominates that
- the sign is apparent

If the proof relies on a plausible but unproved claim, write it as a conjecture or open obligation. Do not camouflage it as intuition.

## Output Format

Use Markdown with LaTeX math.

Recommended structure:

```markdown
## Setup

Define primitives, notation, assumptions, and the exact claim.

## Proof

### Step 1: <goal of the step>

...

### Step 2: <goal of the step>

...

The intuition is ...

\(\square\)
```

If the requested proof cannot be completed, return:

- the strongest partial result proved,
- the exact unproved step or obstruction,
- any counterexample or parameter region found,
- what would be needed to close the gap.
