# Full-season characterization (632 local SportVU games, 2015-16)

Source: `results/clock_alignment_v1.csv` (sha256 77448352542783a8…), source-exact method (ismayc/tracking-study d21f8e3c, reproduction PASS). Leads are per game; calibration labels = shot-team agreement; held-out = turnover-team agreement.

## Game accounting

| stage | games |
|---|---|
| raw_files | 632 |
| parseable | 632 |
| with_tracking_moments | 631 |
| calibratable (>=20 labelled shots, >=5 turnovers) | 631 |
| validated | 437 |
| ambiguous (MULTIMODAL within one event) | 142 |
| drifting (|dH|>2 s) | 40 |
| held-out failures (TO agreement < 0.80) | 12 |

## Lead distribution — CLOCK_CALIBRATION_VALIDATED games

| quantity | value |
|---|---|
| n | 437 |
| median / mean / sd (s) | 4.00 / 4.16 / 1.02 |
| IQR (s) | 3.5 – 5.0 |
| p05 / p95 (s) | 2.5 / 6.0 |
| range (s) | 2.0 – 7.5 |
| shot-team agreement, pooled, naive → calibrated | 0.305 → 0.978 (70,679 calibration shots; median 162/game) |
| per-game shot agreement, median naive → calibrated (min calibrated) | 0.297 → 0.981 (0.828) |
| held-out turnover agreement, pooled, naive → calibrated | 0.382 → 0.936 (11,692 turnovers; median 26/game) |
| per-game turnover agreement, median naive → calibrated (min calibrated) | 0.370 → 0.941 (0.800) |
| all 631 calibrated games (any status): median lead / IQR / shots / turnovers | 4.0 s / 3.5–5.0 / 0.976 / 0.932 |

Lead histogram (validated): 2.0s: 4, 2.5s: 23, 3.0s: 53, 3.5s: 81, 4.0s: 96, 4.5s: 67, 5.0s: 47, 5.5s: 34, 6.0s: 17, 6.5s: 9, 7.0s: 5, 7.5s: 1

## Strata — DESCRIPTIVE_ONLY (no subgroup inference)

| stratum | level | n validated | lead median | mean | IQR |
|---|---|---|---|---|---|
| month | 01 | 103 | 4.00 | 4.12 | 3.5–4.5 |
| month | 10 | 25 | 4.00 | 4.38 | 3.5–5.0 |
| month | 11 | 149 | 4.00 | 4.27 | 3.5–5.0 |
| month | 12 | 160 | 4.00 | 4.05 | 3.5–4.6 |
| half | H1 | 631 | 4.00 | 4.09 | 3.0–5.0 |
| half | H2 | 631 | 4.00 | 4.03 | 3.0–5.0 |
| half | H2-H1 signed | 631 | 0.00 | -0.06 | -1.0–1.0 |

Home-team stratum (30 levels; per-game lead attributed to the home arena's scorer's table) is in `results/strata_descriptive.csv`: lead medians range 3.0–6.0 s across arenas (n per arena 8–18). Home/away as a *game* property is not applicable to a per-game quantity.
File provenance: all 632 files are the linouk23 2015-16 mirror (one file with 466 event containers and zero moments: 0021500659).

First vs second half: per-half leads exist for the 631 calibrated games; H1 median 4.0 s, H2 median 4.0 s; signed H2−H1 median 0.0 s, IQR -1.0–1.0 s.
