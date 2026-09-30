# Prevalence — semantic classes and non-live tracking frames (descriptive)

Universe: 301 games (v3 ∩ SportVU ∩ CLOCK_CALIBRATION_VALIDATED), 59,924 v3 possession rows → possession intervals. Classifier v1 frozen before the results were computed; no rule was changed after results.

## Segment classes

| class | segments | share | frames (naive) | frame share | nominal-duration share | non-live frame share within class |
|---|---|---|---|---|---|---|
| LIVE_CONTINUOUS_PLAY | 37,378 | 0.624 | 12,587,409 | 0.521 | 0.603 | 0.001 |
| FREE_THROW_ADMINISTRATION | 6,414 | 0.107 | 4,221,190 | 0.175 | 0.120 | 0.395 |
| TIMEOUT | 1,970 | 0.033 | 1,078,483 | 0.045 | 0.042 | 0.277 |
| SUBSTITUTION_OR_ADMINISTRATION | 3,671 | 0.061 | 2,359,309 | 0.098 | 0.086 | 0.229 |
| MADE_BASKET_DEAD_BALL | 1,832 | 0.031 | 971,615 | 0.040 | 0.036 | 0.195 |
| OUT_OF_BOUNDS_OR_INBOUND_SETUP | 2,485 | 0.041 | 1,294,382 | 0.054 | 0.045 | 0.257 |
| PERIOD_BOUNDARY | 736 | 0.012 | 190,506 | 0.008 | 0.007 | 0.240 |
| SEGMENTATION_ARTIFACT | 2,254 | 0.038 | 76,951 | 0.003 | 0.003 | 0.133 |
| AMBIGUOUS | 3,184 | 0.053 | 1,371,471 | 0.057 | 0.058 | 0.295 |

Ambiguous share 0.053 (of which 855 have no tracking frames in the interval). SEGMENTATION_ARTIFACT = interval length ≤ 0 (two terminal stamps at the same second) or a row escaping its interval.

## Frame-level prevalence

- Corpus (all deduplicated frames of the 301 games): {'LIVE': 20654658, 'STOPPED_CLOCK': 3534471, 'CLOCK_ANOMALY': 14668, 'GAP_EDGE': 4535, 'total': 24208332}; **non-live share = 0.147**.
- Inside possession intervals: non-live frames = **0.145** of interval frames; intervals containing any non-live frame **0.392**; > 10 % non-live 0.324; > 25 % 0.203; > 50 % 0.035.

## Zero-span row hypothesis (H0: zero-span v3 row = dead ball)

33,996 zero-span rows in the universe. Row-span classes: ZERO_CLOCK_SPAN_BUT_TRACKING_MOVEMENT 31098 (0.915), ZERO_SPAN_NO_TRACKING 2785 (0.082), ZERO_SPAN_STOPPED_BLOCK 113 (0.003).
Fraction of zero-span rows whose possession interval contains ≥ 25 live frames: **0.918**. Under the frozen chains' closed row-span mask these rows yield 22,895 frames, of which 14,789 are stopped-clock.
Reading: a zero-span row is a single-event possession whose row does not span its own play; H0 is rejected for the ZERO_CLOCK_SPAN_BUT_TRACKING_MOVEMENT share and the row-span mask, not the possession, is what selects dead-ball frames.

## Descriptive breakouts (non-live frame share of interval frames; LIVE_CONTINUOUS_PLAY class share)

### by period

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| 1 | 14,378 | 0.124 | 0.696 |
| 2 | 14,204 | 0.143 | 0.662 |
| 3 | 14,106 | 0.146 | 0.653 |
| 4 | 13,795 | 0.164 | 0.617 |
| 5 | 417 | 0.191 | 0.535 |
| 6 | 77 | 0.233 | 0.377 |

### by late_game

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| False | 54,054 | 0.139 | 0.669 |
| True | 2,923 | 0.258 | 0.409 |

### by follows_made_basket

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| False | 36,133 | 0.200 | 0.586 |
| True | 20,844 | 0.058 | 0.778 |

### by has_free_throw

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| False | 50,300 | 0.140 | 0.659 |
| True | 6,677 | 0.183 | 0.631 |

### by has_timeout

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| False | 52,500 | 0.142 | 0.666 |
| True | 4,477 | 0.174 | 0.543 |

### by has_oob_or_violation

| level | segments | non-live frame share | live-class share |
|---|---|---|---|
| False | 54,563 | 0.140 | 0.678 |
| True | 2,414 | 0.245 | 0.158 |

