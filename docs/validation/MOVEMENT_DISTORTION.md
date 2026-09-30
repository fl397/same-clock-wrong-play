# Distortion of M1/M2/M3 under NAIVE_PBP_POSSESSION vs LIVE_PLAY_ONLY

Universe 301 games, 59,924 segments; metrics and conditions frozen in `configs/LIVE_PLAY_CLASSIFIER.yaml` v1 (frozen before any comparison). Naive = all frames in (end+lead, prev_end+lead]; live-only = running-clock frames; a value needs ≥ 25 usable frames.

| level | metric | n pairs | mean naive | mean live | paired Δ (naive − live) | standardized Δ | Pearson | Spearman | MAE | median |Δ| | p90 |Δ| | naive-only (no live value) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| possession | M1 player speed (ft/s) | 56,614 | 6.614 | 6.906 | -0.293 | -0.180 | 0.919 | 0.894 | 0.318 | 0.000 | 1.180 | 51 |
| possession | M2 offensive spacing hull (sq ft) | 56,614 | 484.856 | 481.348 | +3.508 | +0.021 | 0.914 | 0.939 | 29.888 | 0.000 | 99.972 | 51 |
| possession | M3 team dispersion (ft) | 56,614 | 14.940 | 14.846 | +0.094 | +0.035 | 0.911 | 0.922 | 0.516 | 0.000 | 1.832 | 51 |
| game_team | M1 player speed (ft/s) | 602 | 6.607 | 6.901 | -0.294 | -0.974 | 0.954 | 0.952 | 0.294 | 0.287 | 0.414 |  |
| game_team | M2 offensive spacing hull (sq ft) | 602 | 484.432 | 480.946 | +3.486 | +0.102 | 0.964 | 0.963 | 7.565 | 6.097 | 15.964 |  |
| game_team | M3 team dispersion (ft) | 602 | 14.933 | 14.839 | +0.094 | +0.172 | 0.960 | 0.960 | 0.142 | 0.115 | 0.295 |  |
| team_season | M1 player speed (ft/s) | 30 | 6.607 | 6.903 | -0.296 | -1.481 | 0.986 | 0.969 | 0.296 | 0.299 | 0.334 |  |
| team_season | M2 offensive spacing hull (sq ft) | 30 | 486.337 | 482.889 | +3.447 | +0.175 | 0.990 | 0.980 | 3.643 | 3.085 | 7.190 |  |
| team_season | M3 team dispersion (ft) | 30 | 14.958 | 14.864 | +0.094 | +0.355 | 0.979 | 0.978 | 0.094 | 0.082 | 0.185 |  |

## Team-season ranks (30 teams)

| metric | rank Spearman | max |rank shift| | median |rank shift| | teams whose rank changes |
|---|---|---|---|---|
| M1 | 0.969 | 5 | 1.0 | 21 |
| M2 | 0.980 | 4 | 1.0 | 23 |
| M3 | 0.978 | 5 | 1.0 | 25 |

## Context dependence (construct check, |naive − live| per possession)

| metric | clean n | clean median | clean p90 | non-live n | non-live median | non-live p90 | MWU p (two-sided, descriptive) |
|---|---|---|---|---|---|---|---|
| M1 | 37,375 | 0.000 | 0.000 | 16,192 | 0.697 | 1.942 | 0.00e+00 |
| M2 | 37,375 | 0.000 | 0.000 | 16,192 | 62.704 | 210.387 | 0.00e+00 |
| M3 | 37,375 | 0.000 | 0.000 | 16,192 | 1.154 | 3.580 | 0.00e+00 |

Clean = LIVE_CONTINUOUS_PLAY (by construction |Δ| ≈ 0 there: ≥ 95 % of frames are live); non-live = TIMEOUT / FREE_THROW / SUBSTITUTION_OR_ADMIN / OOB / MADE_BASKET classes. Median |Δ| by non-live class: M1: FREE_THROW_ADMINISTRATION 1.20, MADE_BASKET_DEAD_BALL 0.32, OUT_OF_BOUNDS_OR_INBOUND_SETUP 0.34, SUBSTITUTION_OR_ADMINISTRATION 0.63, TIMEOUT 0.65; M2: FREE_THROW_ADMINISTRATION 68.13, MADE_BASKET_DEAD_BALL 41.89, OUT_OF_BOUNDS_OR_INBOUND_SETUP 82.03, SUBSTITUTION_OR_ADMINISTRATION 50.33, TIMEOUT 73.33; M3: FREE_THROW_ADMINISTRATION 1.23, MADE_BASKET_DEAD_BALL 0.67, OUT_OF_BOUNDS_OR_INBOUND_SETUP 1.68, SUBSTITUTION_OR_ADMINISTRATION 0.85, TIMEOUT 1.45

## timeout windows — structure only

Windows with ≥ 1 member possession in the universe: 4,561; with ≥ 1 non-live-class member: **0.995**; member possessions in a non-live class: 0.287; member interval frames that are non-live: **0.152**; of the frames the frozen chain actually consumed (closed row-span mask), stopped-clock share: **0.117**. No TSS or effect quantity is computed here.

## Note on the row-span statistic (axis)
The classifier defines the row span on the **calibrated** axis (`[end + lead, start + lead]`). The companion timeout-window chain masked the row span on the **uncalibrated** PBP axis (lead 0), where an earlier analysis documented 10,342 "valid" PFVs on zero-span rows. The 0.117 stopped-clock share above therefore describes the calibrated row-span mask, not byte-for-byte what that chain consumed; No rule was changed to reconcile the two; both are reported.

## Reading
Dead-ball contamination is a **systematic, mostly uniform bias plus possession-level noise**, not a re-ranking force: naive speed is 0.29 ft/s (4.3 %) too low and naive spacing/dispersion slightly too high; possession-level agreement r ≈ 0.91–0.92 with p90 |Δ| of 1.2 ft/s / 100 sq ft / 1.8 ft; team-season ranks move by a median of one place (max 4–5; ρ ≥ 0.97). The distortion is concentrated where the semantics predict it (): median |Δ| is exactly 0 in clean possessions and 0.70 ft/s / 63 sq ft / 1.15 ft in possessions with a non-live component, largest for free-throw administration.
