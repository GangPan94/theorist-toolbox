---
name: proof-readability
description: Polish verified mathematical proofs without changing their mathematical content. Use after a proof has been accepted by the user, a reviewer, Lean, or a co-math review cycle; or when asked to improve proof exposition, readability, signposting, notation, references, or grammar while preserving the original argument.
---

# Proof Readability

Edit only proofs whose correctness has already been accepted. This is an exposition pass, not a proving pass.

Prime invariant: never change the mathematics. Do not strengthen, weaken, replace, or silently repair an argument. If you find a real gap, stop editing that proof and report the gap precisely.

## Preconditions

Before editing, confirm one of:

- the user says the proof is already verified,
- a co-math workstream has an approval file,
- a Lean build or other formal check accepted the statement,
- the task is explicitly limited to readability comments rather than direct edits.

If correctness is not established, offer a `math-proof` or `codex-math` verification pass first.

## Six-Layer Pass

Work in this order:

1. **Architecture**: restate deferred results, add proof sketches where appropriate, make theorem/lemma roles clear, close composite proofs explicitly.
2. **Signposting**: add proof openers, named steps, exhaustive case labels, assumption open/close markers, and goal statements before algebra.
3. **Line-level justification**: add reasons for inequalities, signs, substitutions, citations, and relation chains.
4. **Notation hygiene**: define symbols before use, recall object types, stabilize names, check argument order, and avoid notation dumps.
5. **Intuition**: add short "in words" or intuition paragraphs outside the formal proof. Keep every intuition sentence literally defensible.
6. **Sentence and formula grammar**: make formulas part of grammatical sentences, avoid starting sentences with symbols, replace logical shorthand in prose, and run read-aloud checks.

## Safe Edits

- Add signposts and roadmap sentences.
- Expand an algebraic step already implicit in the proof.
- Move definitions earlier when the definition itself is unchanged.
- Fix references, labels, theorem names, punctuation, and prose grammar.
- Add intuition after the proof or outside the formal argument.

## Contested Edits

Propose these in a report; do not apply them without explicit approval:

- replacing a contradiction proof with a direct proof,
- merging or splitting lemmas,
- changing standing assumptions,
- changing theorem statements, quantifiers, bounds, or conclusions,
- reordering an equality or inequality chain when the new order itself needs proof.

## Banned Phrases

Remove or replace:

- clearly,
- obviously,
- it is easy to see,
- straightforward,
- similar argument omitted,
- by inspection,
- this dominates that,
- follows naturally.

Replace each with the actual reason, a precise reference, or a flagged gap.

## Report

When done, summarize:

- edits by layer,
- any suspected gaps that were not edited,
- any derived intermediate lines that need correctness spot-checking,
- contested edits proposed but not applied,
- remaining unresolved references or undefined symbols.
