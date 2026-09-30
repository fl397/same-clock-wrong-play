# Live-play classifier — pre-result specification

Frozen 2026-09-19, before any segment table, prevalence number or M1/M2/M3 comparison exists. Rules: `configs/LIVE_PLAY_CLASSIFIER.yaml` (version 1). This document records *why* each rule is stated as it is and what was looked at before the rules were fixed.

## What was inspected before freezing (semantic exploration only — no metric, no comparison)
1. `possessions_v3.parquet` structure: 173,718 rows; `start_clock` is the clock of the row's first PBP event and `end_clock` that of its terminal event (verified on game 0021500001 against `pbp_with_clock`: e.g. row "681.0 → 681.0, made_shot, n_pbp_rows 1" is the Morris jumper at 681; the preceding row ends at 697 — the possession's real interval is 697 → 681). Hence **99,041 zero-span rows are single-event possessions, not zero-duration possessions**. Terminal events of zero-span rows: made_shot 34,861; missed_shot_def_rebound 34,775; turnover 14,086; free_throw_made 11,353; made_shot_and1 1,822; interrupted 1,235; period_end 805; game_end 53; interrupted_by_ft 51. Negative spans: 162.
2. PBP rows between possessions (fouls, substitutions, timeouts, replays, jump balls) belong to no v3 row; they are recovered by the `(prev_end_actionNumber, end_actionNumber]` rule.
3. Tracking clock behaviour on one game (10.27.2015.DET.at.ATL, deduplicated on (period, utc): 82,969 frames): consecutive-frame utc gap is 40 ms at the median and 99.9th percentile ≈ 41 ms with 100 gaps > 1 s (the archive omits most dead time); game-clock steps are −0.04 s at the median; 76 runs of identical clock with ≥ 5 frames hold 14.0 % of the frames, the longest 375 frames ≈ 27 s of utc (timeouts / free throws by clock value); 103 frames show a clock increase (anomalies). This established that (a) a stopped clock is directly observable per frame and (b) stopped-clock frames are a sizeable minority worth auditing — no movement quantity was computed.

## Design decisions
- **Segment = possession interval `(end, prev_end]`**, not the v3 row span, because the audit asks what a possession-based analysis *intends* to select; the row span is carried as `row_span_class` so that the frozen chains' actual selection is also characterised. The half-open convention assigns a stopped block sitting at a terminal stamp to the following segment (it is that segment's inbound / free-throw set-up).
- **Live = game clock running.** NBA rules stop the clock exactly when the ball is dead; this makes the frame criterion semantic (rule-based) and independent of player movement. Stationary players in live play remain LIVE. Clock anomalies and gap edges are non-live because no velocity is definable there.
- **Class priority** puts `LIVE_CONTINUOUS_PLAY` (f_live ≥ 0.95, ≥ 25 frames) ahead of the semantic dead-ball causes, so a possession that merely *follows* a made basket but whose frames show a running clock throughout is live, not "made-basket dead ball"; semantic causes label the *nature* of the non-live component when one exists. Multi-label flags are stored for breakouts.
- **Zero-span hypothesis** is tested per row (`row_span_classes`), never assumed.
- **Metrics M1/M2/M3, conditions, thresholds (25 frames, 0.10 s, 40 ft/s), aggregation and distortion statistics** are fixed here; no metric may be added or altered after results.
- **/ ** comparisons are defined here in full.

## Universe
v3 ∩ SportVU-with-moments ∩ CLOCK_CALIBRATION_VALIDATED (shared table). Expected 301 games (the 449 tracking games contain 301 validated leads); the exact list is written by the producer to `results/universe_games.csv`.

## Commit
This file and the YAML are committed before `src/build_segments.py` is run; the rule version is stamped into `results/segments_summary.json` by the producer.
