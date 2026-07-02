# Conjecture Exploration Prompt

Use this when you do not yet know whether a claim is true.

```text
Use the Theorist Toolbox conjecture exploration workflow.

Conjecture:
<state exact claim>

Definitions and domains:
<paste all notation, parameters, constraints, and model equations>

What has been tried:
<direct proof attempt, numerical tests, failed strategies, known special cases>

Explore:
- Search for counterexamples first.
- If the global claim appears false, identify a weaker true statement or sufficient conditions.
- If it appears true, propose a proof strategy and prove any tractable intermediate lemma.
- Do not infer the general result from examples.
- Give reproducible parameter values for any counterexample.

Return:
- current status,
- analytic evidence,
- numerical or example evidence,
- counterexamples if found,
- strongest clean next proof target.
```
