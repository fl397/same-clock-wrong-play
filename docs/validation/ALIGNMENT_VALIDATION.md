# Global +4 s vs per-game calibration (producer: src/global_shift.py)

Primary evaluation: held-out turnover-team agreement (never used to choose a lead). M1 = +4.0 s is the only global offset evaluated (the previously observed corpus median).

## All 631 calibratable games

| method | pooled agreement | n turnovers | per-game median | p05 | p25 | p75 | p95 | games ≥ 0.90 | games ≥ 0.95 | worst-decile mean |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 naive 0 s | **0.393** | 16,943 | 0.385 | 0.207 | 0.316 | 0.467 | 0.594 | 0.0 % | 0.0 % | 0.200 |
| M1 global +4.0 s | **0.942** | 16,965 | 0.951 | 0.857 | 0.913 | 0.971 | 1.000 | 83.8 % | 52.3 % | 0.847 |
| M2 per-game | **0.932** | 16,968 | 0.939 | 0.830 | 0.903 | 0.967 | 1.000 | 77.2 % | 44.1 % | 0.821 |

## CLOCK_CALIBRATION_VALIDATED games (437)

| method | pooled agreement | n turnovers | per-game median | p05 | p25 | p75 | p95 | games ≥ 0.90 | games ≥ 0.95 | worst-decile mean |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 naive 0 s | **0.382** | 11,682 | 0.370 | 0.200 | 0.306 | 0.455 | 0.579 | 0.0 % | 0.0 % | 0.194 |
| M1 global +4.0 s | **0.944** | 11,665 | 0.955 | 0.857 | 0.917 | 0.974 | 1.000 | 86.0 % | 54.9 % | 0.852 |
| M2 per-game | **0.936** | 11,692 | 0.941 | 0.850 | 0.905 | 0.968 | 1.000 | 79.2 % | 45.3 % | 0.839 |

## Secondary structural metrics (validated games for screens; all calibratable for windows)

| metric | M0 naive | M1 global +4 s | M2 per-game |
|---|---|---|---|
| 1. shot-window wrong-team rate | 0.690 | 0.035 | 0.024 |
| 2. turnover-window wrong-team rate | 0.607 | 0.058 | 0.068 |
| 3. apparent screen onset < 0.5 s (7,625 detected on-ball screens, 301 games) | 27.7 % | 4.7 % | 4.5 % |
| 4. screen possession reassignment vs M0 | — | 23.0 % | 23.9 % |
| median screen onset (s) | 8.04 | 4.52 | 5.50 |

## M2 − M1 (held-out turnovers) overall and by frozen taxonomy class

| class | games | pooled M1 | pooled M2 | pooled M2−M1 | per-game mean diff | per-game median diff | games M2 better | games M1 better | games M1 < 0.90 | games M2 < 0.90 | median |lead − 4| |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | 631 | 0.942 | 0.932 | **-0.010** | -0.011 | +0.000 | 19.3 % | 31.4 % | 16.2 % | 22.8 % | 0.5 s |
| SHARP_UNIMODAL | 142 | 0.944 | 0.935 | **-0.008** | -0.009 | +0.000 | 18.3 % | 28.2 % | 14.8 % | 21.8 % | 0.5 s |
| FLAT_PLATEAU | 302 | 0.943 | 0.932 | **-0.011** | -0.011 | +0.000 | 18.2 % | 32.8 % | 15.2 % | 22.2 % | 0.5 s |
| MULTIMODAL | 120 | 0.944 | 0.939 | **-0.005** | -0.005 | +0.000 | 20.0 % | 27.5 % | 15.0 % | 17.5 % | 0.5 s |
| DRIFTING | 67 | 0.931 | 0.911 | **-0.020** | -0.020 | +0.000 | 25.4 % | 38.8 % | 25.4 % | 37.3 % | 1.0 s |

Reading rule (frozen): M1 is judged only on held-out turnovers; no spacing/eFG/Timeout quantity was consulted.

## Analysis definitions

Question: if the median latency is four seconds, does a single global shift of the whole corpus work as well as a per-game offset?

Comparison, defined before any number was computed (`configs/global_shift_baseline.yaml`): **M0** naive 0 s · **M1** global +4.0 s (the previously observed full-corpus median; the only global offset that will ever be evaluated — no ±0.5 s grid) · **M2** per-game `calibrated_lead_s` from `results/clock_alignment_v1.csv`. Primary evaluation = **held-out turnover-team agreement only** (labels never used to pick a lead), with the unchanged source labeler (nearest-player heuristic, `[c+lead, c+lead+2.0 s]`, ≥ 5 frames, majority). Universe = all 631 calibratable games; validated-only rows reported alongside; class breakdown by the pre-specified class definitions.

Statistics: pooled agreement, per-game median, p05/p25/p75/p95, fraction of games ≥ 0.90 and ≥ 0.95, worst-decile mean; M2 − M1 overall and by SHARP_UNIMODAL / FLAT_PLATEAU / MULTIMODAL / DRIFTING. Secondary structural metrics at each method's lead: shot-window wrong-team rate, turnover-window wrong-team rate, apparent screen onset < 0.5 s, screen possession reassignment (same code paths as the consequence producer). No basketball outcome enters the comparison. Producer: `src/global_shift.py`.
