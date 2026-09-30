# Figure 1 — reading the corrected quartile pattern

Figure 1 compares effective field-goal percentage by offensive-spacing quartile on the 26,177 shots common to both alignments.

Naive equal-clock join: 48.5 / 53.2 / 54.7 / 57.7 % (monotone; Q4 - Q1 = +9.2 points).
Corrected join: 54.6 / 51.5 / 53.0 / 54.9 % (Q4 - Q1 = +0.3 points).

The corrected quartile pattern is non-monotonic, with an elevated Q1. We therefore interpret the result only as evidence
that the strong monotonic naive gradient is not robust to proper alignment; we do not assign a causal interpretation to
the residual corrected quartile pattern.

Two things this figure does **not** claim:

- it does not claim that the corrected quartiles are equal - they are not (Q1 54.6 % sits above Q2 51.5 % and Q3 53.0 %);
- it does not claim that offensive spacing is unrelated to shooting efficiency in every form. The comparison is between
  two joins of the same shots, not a study of spacing.

UNTESTED HYPOTHESIS (not evaluated in this work, recorded here only so the open question is on the record): the tightest
corrected spacing quartile may differ in shot mix - for example a larger share of rim or post attempts - which would move
eFG without any spacing effect. Nothing in this repository tests that, and it appears in no abstract, figure, caption or
README claim.

Rules and decision criteria for the matched-shot comparison: `docs/validation/MATCHED_SHOT_VALIDATION.md`; results:
`docs/validation/MATCHED_SHOT_VALIDATION.md`, `results/matched_shot_audit.json`.
