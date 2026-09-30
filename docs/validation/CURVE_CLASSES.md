# Calibration-uncertainty classes (rules: configs/CURVE_TAXONOMY.yaml)

| class | n | fraction | plateau width median (IQR) s | abs half-diff median (p75) s | argmax − rising edge median s | lead median | shots calibrated | TO naive → calibrated | holdout-fail n | validated n |
|---|---|---|---|---|---|---|---|---|---|---|
| SHARP_UNIMODAL | 142 | 0.225 | 2.0 (1.5–2.0) | 0.5 (1.0) | 0.5 | 4.0 | 0.978 | 0.383 → 0.935 | 4 | 138 |
| FLAT_PLATEAU | 302 | 0.478 | 3.0 (2.5–3.5) | 1.0 (1.5) | 1.0 | 4.0 | 0.977 | 0.382 → 0.932 | 3 | 299 |
| MULTIMODAL | 120 | 0.190 | 3.0 (2.5–4.0) | 1.0 (1.5) | 1.0 | 4.0 | 0.976 | 0.413 → 0.939 | 0 | 0 |
| DRIFTING | 67 | 0.106 | 3.5 (3.0–4.0) | 2.5 (3.0) | 1.5 | 4.5 | 0.971 | 0.429 → 0.911 | 5 | 0 |
| INSUFFICIENT | 1 | 0.002 | 8.5 (8.5–8.5) | 0.0 (0.0) | 0.0 | 0.0 | nan | nan → nan | 0 | 0 |

Argmax − rising-edge over all calibrated games: median 1.0 s, IQR 0.5–1.5 s; distribution: 0.0s: 81, 0.5s: 174, 1.0s: 167, 1.5s: 109, 2.0s: 57, 2.5s: 22, 3.0s: 17, 3.5s: 2, 4.0s: 2

Reading: the source-exact argmax is retained. On FLAT_PLATEAU curves the lead is only identified to within the plateau width; the held-out turnover agreement stays high in every shape class (the 2-s label window is tolerant), so plateau width is an *identification* limitation for boundary shifting, not a labelling failure. HOLDOUT_FAIL is reported per class as a validation outcome.

## Analysis definitions

The rules below were fixed before any taxonomy count or consequence metric was computed. Machine-readable definitions: `configs/CURVE_TAXONOMY.yaml`,
`configs/CONSEQUENCE_METRICS.yaml`. Inputs: `results/clock_alignment_v1.csv` (sha256 77448352…) only, plus the
existing per-game JSON curves, the existing v3 possession table, existing detected on-ball screen events and existing timeout windows.

Deliberately not done: no new calibration method, no plateau-aware lead, no re-choice of any lead, no coverage-increasing rule.
The source-exact argmax is preserved; its known limitation (argmax above the rising edge on plateau curves) is characterised
by the `rising_edge_lead_s` column and the FLAT_PLATEAU class.

Precedence (first match): INSUFFICIENT → DRIFTING → MULTIMODAL → FLAT_PLATEAU (plateau ≥ 2.5 s at tolerance 0.02) → SHARP_UNIMODAL.
The 2.5-s threshold is set a priori from the 2.0-s label window (leads inside one window are indistinguishable by construction).

Consequence metrics A–D are defined in the YAML with their exact populations and reporting; they are structural
(assignment / timing / membership) quantities and contain no basketball outcome.
