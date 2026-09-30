# Structural consequences of naive vs calibrated timing (rules: configs/CONSEQUENCE_METRICS.yaml)

Validated games: 437. No basketball outcome is reported.

## A. Possession / team-assignment change

| event type | naive team disagreement | calibrated | change fraction (bounds, all validated games) | exact change fraction (40-game random subsample, seed 20260919) | n events (subsample) |
|---|---|---|---|---|---|
| shots | 0.695 | 0.022 | 0.673 – 0.718 | **0.697** | 6,101 (+336 naive-unlabelled) |
| turnovers | 0.618 | 0.064 | 0.554 – 0.682 | **0.608** | 1,015 (+22 naive-unlabelled) |

Screens (existing detected on-ball screen events, 7,625 events in 301 validated games): **23.8 %** are assigned to a different v3 possession once the tracking clock is mapped to the PBP axis with the calibrated lead; 0.7 % fall into a gap between possessions; 2.1 % had more than one candidate (first taken).

## B. Event-relative time error (|calibrated − naive| tracking instant = per-game lead)

| events | n | p05 | p25 | p50 | p75 | p95 | mean | ≥ 2 s | ≥ 4 s |
|---|---|---|---|---|---|---|---|---|---|
| shots | 70,679 | 2.5 | 3.5 | 4.0 | 5.0 | 6.0 | 4.16 | 100.0 % | 63.1 % |
| turnovers | 11,692 | 2.5 | 3.5 | 4.0 | 4.5 | 6.0 | 4.11 | 100.0 % | 61.2 % |

SportVU event-container ids match PBP `actionNumber` for 95.5 % of shots / 95.2 % of turnovers; of the matched containers only 61.1 % / 54.8 % have a clock span overlapping the calibrated label window — the id join does not remove the clock offset.

## C. Early-possession misclassification (detected on-ball screens: onset after possession start)

| axis | n | median onset (s) | p10 | p90 | < 0.25 s | < 0.5 s | < 1.0 s | negative |
|---|---|---|---|---|---|---|---|---|
| naive | 7,625 | 8.02 | 0.01 | 17.44 | 26.2 % | 28.1 % | 30.5 % | 0.4 % |
| calibrated | 7,573 | 5.50 | 1.20 | 18.21 | 2.3 % | 4.5 % | 8.4 % | 0.0 % |

## D. Window membership change (existing timeout windows; tracking frames)

| population | member possessions | naive frames | fraction of naive frames leaving the window | calibrated frames |
|---|---|---|---|---|
| all | 85,277 | 13,547,492 | **46.2 %** | 10,843,723 |
| zero_span | 47,987 | 1,729,100 | **100.0 %** | 29,823 |
| positive_span | 37,290 | 11,818,392 | **38.4 %** | 10,813,900 |

Windows: 4,561 in 301 games; median per-window change 46.9 %; windows changing > 25 %: 96.7 %, > 50 %: 41.6 %.
Zero-span rows are v3 possessions with identical start and end clock; their naive frames are stopped-clock frames at one clock value and vanish under any shift (the live-play analysis characterises them).

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
