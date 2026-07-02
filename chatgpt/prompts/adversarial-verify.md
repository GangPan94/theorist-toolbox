# Adversarial Verification Prompt

Use this to audit a proof.

```text
Use the Theorist Toolbox adversarial verification workflow.

Statement:
<paste theorem/lemma/proposition>

Proof to audit:
<paste proof>

Relevant definitions, assumptions, and equations:
<paste context>

Audit requirements:
- Walk through the proof step by step.
- Classify each nontrivial step as OK, GAP, ERROR, or UNCLEAR.
- Check signs, inequality directions, edge cases, hidden assumptions, and theorem statement match.
- Treat examples and numerical evidence as evidence only, not proof.
- Report concrete findings only; distinguish real gaps from false positives.

Return:
1. Verdict: PASS, PASS WITH CAVEATS, FAIL, or INCONCLUSIVE.
2. Findings with severity, location, issue, why it matters, and suggested fix.
3. A list of what you checked.
```
