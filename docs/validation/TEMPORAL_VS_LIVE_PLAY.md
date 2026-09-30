# Temporal misalignment vs non-live frames: a 2×2 design (producer: src/temporal_semantic_2x2.py)

Universe: 301 validated games, 57,808 possession intervals (same set in all cells; paired statistics on intervals with a value in all four cells).

## M4 — event/window team-assignment agreement (held-out turnovers; shots secondary)

| cell | clock | frames | turnover agreement | n | shot agreement | n |
|---|---|---|---|---|---|---|
| A | naive 0 s | raw | **0.384** | 8,048 | 0.303 | 47,110 |
| B | naive 0 s | live-only | **0.388** | 8,025 | 0.303 | 47,062 |
| C | calibrated | raw | **0.935** | 8,044 | 0.977 | 48,784 |
| D | calibrated | live-only | **0.935** | 8,043 | 0.977 | 48,775 |

## M1–M3 (paired on intervals valid in all cells)

### M1 (ft/s) — paired n = 56,033; valid per cell A/B/C/D = 56,618/56,374/56,665/56,614

| cell | mean | SD |
|---|---|---|
| A | 6.974 | 1.975 |
| B | 7.301 | 1.865 |
| C | 6.627 | 1.700 |
| D | 6.919 | 1.611 |

| contrast | paired mean diff | standardized (÷ SD_D) | MAE | p90 abs | Spearman |
|---|---|---|---|---|---|
| A−B (semantic) | -0.327 | -0.203 | 0.350 | 1.245 | 0.886 |
| A−C (temporal) | +0.347 | +0.215 | 0.856 | 1.981 | 0.770 |
| A−D (combined) | +0.054 | +0.034 | 1.022 | 2.430 | 0.650 |
| B−D (temporal given live) | +0.382 | +0.237 | 0.901 | 2.097 | 0.720 |
| C−D (semantic given calibrated) | -0.293 | -0.182 | 0.318 | 1.179 | 0.892 |

Decomposition: temporal A→C +0.347, semantic A→B -0.327, combined A→D +0.054, interaction +0.035 (mean diffs); MAE temporal 0.856, semantic 0.350, combined 1.022.

### M2 (sq ft) — paired n = 56,033; valid per cell A/B/C/D = 56,618/56,374/56,665/56,614

| cell | mean | SD |
|---|---|---|
| A | 574.796 | 175.028 |
| B | 580.316 | 161.570 |
| C | 486.717 | 183.608 |
| D | 483.310 | 166.287 |

| contrast | paired mean diff | standardized (÷ SD_D) | MAE | p90 abs | Spearman |
|---|---|---|---|---|---|
| A−B (semantic) | -5.520 | -0.033 | 32.980 | 113.082 | 0.912 |
| A−C (temporal) | +88.079 | +0.530 | 104.035 | 227.451 | 0.739 |
| A−D (combined) | +91.486 | +0.550 | 117.741 | 263.948 | 0.664 |
| B−D (temporal given live) | +97.006 | +0.583 | 111.376 | 236.567 | 0.719 |
| C−D (semantic given calibrated) | +3.407 | +0.020 | 29.913 | 100.192 | 0.939 |

Decomposition: temporal A→C +88.079, semantic A→B -5.520, combined A→D +91.486, interaction +8.927 (mean diffs); MAE temporal 104.035, semantic 32.980, combined 117.741.

### M3 (ft) — paired n = 56,033; valid per cell A/B/C/D = 56,618/56,374/56,665/56,614

| cell | mean | SD |
|---|---|---|
| A | 16.705 | 2.713 |
| B | 16.767 | 2.413 |
| C | 14.972 | 2.952 |
| D | 14.879 | 2.632 |

| contrast | paired mean diff | standardized (÷ SD_D) | MAE | p90 abs | Spearman |
|---|---|---|---|---|---|
| A−B (semantic) | -0.063 | -0.024 | 0.555 | 2.045 | 0.883 |
| A−C (temporal) | +1.733 | +0.658 | 2.012 | 4.310 | 0.661 |
| A−D (combined) | +1.825 | +0.694 | 2.252 | 4.947 | 0.554 |
| B−D (temporal given live) | +1.888 | +0.717 | 2.140 | 4.476 | 0.619 |
| C−D (semantic given calibrated) | +0.092 | +0.035 | 0.516 | 1.835 | 0.921 |

Decomposition: temporal A→C +1.733, semantic A→B -0.063, combined A→D +1.825, interaction +0.155 (mean diffs); MAE temporal 2.012, semantic 0.555, combined 2.252.

## Analysis definitions

Question: are clock misalignment and non-live possession content two distinct failure modes, or two labels for one problem?

|                  | RAW SEMANTICS | LIVE-PLAY FILTER |
|---|---|---|
| NAIVE CLOCK (0 s) | **A** | **B** |
| CALIBRATED CLOCK (per game) | **C** | **D** |

Same game/possession intersection in all four cells (the 301-game live-play universe; possession intervals `(end, prev_end]` mapped with the cell's lead; the frame-level live criterion of `configs/LIVE_PLAY_CLASSIFIER.yaml` v1). Exactly three movement outputs — M1 mean offensive speed, M2 five-player hull area, M3 centroid dispersion — with the live-play definitions (≥ 25 usable frames), plus one structural output M4 = held-out turnover-window team-assignment agreement computed from each cell's frames. Report per metric: mean, SD, paired A−B / A−C / A−D, standardized difference, Spearman A vs D, MAE; M4 agreement per cell. Decompose descriptively: temporal A→C, semantic A→B, combined A→D; interaction reported; additivity not forced. No metric was added after the results were computed. Producer: `src/temporal_semantic_2x2.py`; config `configs/temporal_semantic_2x2.yaml`.
