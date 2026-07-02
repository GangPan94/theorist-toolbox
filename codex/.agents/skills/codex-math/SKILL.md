---
name: codex-math
description: Run an adversarial mathematical workflow in Codex: verify proofs, write hard proofs, explore conjectures, search for counterexamples, and triage possible gaps. Use for important theorem checks, failed proof attempts, conjectures, independent verification, or requests like "audit this proof", "find a counterexample", "explore this claim", or "verify the math".
---

# Codex Math

Use Codex as an adversarial mathematical co-processor. The goal is not to sound convincing; the goal is to separate proved facts, real gaps, false alarms, and promising leads.

Treat every generated argument as a lead, not a verdict. A proof that looks polished can still be false. A reviewer objection can still be a false positive. Triage every finding.

## Mode Selection

- **Verify** when the user provides a proof, theorem, lemma, or paper section and wants an audit.
- **Write** when the user provides a precise result and asks for a proof.
- **Explore** when the result may be false, under-specified, or hard enough that counterexample search and sufficient conditions are valuable.

For high-stakes claims, use two passes: one constructive pass and one hostile pass. In Codex environments that expose subagents, spawn independent verifier/explorer agents only when the user explicitly asks for parallel or independent agents.

## Verify Mode

1. Extract the exact statement, hypotheses, definitions, and proof block.
2. Build a dependency list: equations, lemmas, citations, domain restrictions, and hidden regularity assumptions.
3. Walk the proof step by step. Classify each step as:
   - `OK`: justified by a definition, prior result, explicit algebra, or standard theorem.
   - `GAP`: a necessary implication is missing.
   - `ERROR`: the step is false, with a counterexample or algebraic correction.
   - `UNCLEAR`: the step might be right but needs a missing definition, citation, or convention.
4. Check signs, dimensions, boundary cases, quantifiers, and whether examples are being used as proof.
5. Triage findings. Report only issues you can explain concretely.

Verification output:

```markdown
## Verdict
PASS | PASS WITH CAVEATS | FAIL | INCONCLUSIVE

## Findings
1. Severity: blocking | major | minor
   Location:
   Issue:
   Why it matters:
   Suggested fix:

## Checked
- Definitions:
- Algebra/signs:
- Edge cases:
- Citations or external results:
```

## Write Mode

1. Restate the theorem with full domains and quantifiers.
2. Identify the most likely proof strategy and at least one fallback strategy.
3. Draft the proof using the `math-proof` discipline: explicit steps, algebra, signs, and edge cases.
4. Run an adversarial self-audit of the proof before returning it.
5. Mark any unresolved step as conjectural or open. Do not hide it inside prose.

After writing, recommend an independent verification pass for important results.

## Explore Mode

Use when the truth of a claim is uncertain.

1. State the exact conjecture and all domains.
2. Search for counterexamples before trying to prove the strongest version.
3. Try special cases only as evidence; never conclude the general result from them.
4. If the global claim fails, identify the boundary: sufficient conditions, necessary conditions, or a weaker true statement.
5. Use deterministic computation when useful. For numerical exploration, save code and make the counterexample reproducible.

Exploration output:

```markdown
## Current Status
Likely true | likely false | true under conditions | unresolved

## Evidence
- Analytic:
- Numerical:
- Counterexamples:

## Next Proof Target
<the strongest clean statement that appears defensible>
```

## Prompt Quality Checklist

Before verifying or exploring, make sure the prompt or extracted context includes:

- the exact claim,
- all notation and domains,
- the relevant definitions and equations,
- what has already been tried,
- what counts as a valid proof or counterexample.

When context is missing, ask for it or explicitly state the assumption you are making.
