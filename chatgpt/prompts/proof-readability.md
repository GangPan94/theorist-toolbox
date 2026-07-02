# Proof Readability Prompt

Use this only after a proof is already accepted as correct.

```text
Use the Theorist Toolbox proof-readability workflow.

Verified proof:
<paste proof>

Statement and nearby context:
<paste theorem statement, definitions, and cited results>

Audience:
<e.g. economics/game-theory journal readers>

Hard invariant:
Do not change the mathematics. Do not change hypotheses, conclusions, quantifiers, bounds, or proof strategy. If you find a gap, stop and report it instead of fixing it silently.

Edit for:
- architecture,
- signposting,
- line-level justifications,
- notation hygiene,
- intuition outside the formal proof,
- sentence and formula grammar.

Return the polished proof plus a report listing edits, suspected gaps, derived intermediate lines that need spot-checking, and contested edits proposed but not applied.
```
