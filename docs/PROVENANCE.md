# Provenance

## Tracking (not redistributed)
- Source: public 2015-16 NBA SportVU mirror, GitHub `linouk23/NBA-Player-Movements` (raw game JSON, one file per game, named `MM.DD.YYYY.AWAY.at.HOME.json`). 632 files were available locally; 631 contain tracking moments (one file, game 0021500659, has 466 event containers and zero moments).
- Structure: each file holds event containers keyed by the play-by-play `eventId`; each container carries moments `[period, utc_ms, game_clock, shot_clock, _, [[team_id, player_id, x, y, z], …]]` at 25 Hz; the ball is `team_id = −1`. Consecutive containers overlap heavily (raw moments ≈ 2.6 × unique `(period, utc_ms)` moments per game). The calibration engine de-duplicates on `(period, game_clock, player_id)`, keep-first, exactly as the source method does; stopped-clock frames (same game clock, different wall clock; ≈ 17 % of unique moments) are a separate phenomenon handled by the live-play classifier (`docs/validation/DEDUPLICATION.md`).
- Court: 94 × 50 ft, x along the length; midcourt x = 47.

## Play-by-play (not redistributed)
- Source: `stats.nba.com` endpoint **PlayByPlayV3**, pulled with the `nba_api` Python package (`nba_api.stats.endpoints.playbyplayv3`; game list from `leaguegamelog`, Regular Season 2015-16). 1,230 games, 599,827 rows.
- Columns used: `gameId, actionNumber, clock ("PT11M41.00S"), period, teamId, personId, actionType, subType, shotResult, isFieldGoal, shotValue, shotDistance, location, scoreHome, scoreAway, description`.
- Shots for calibration: `isFieldGoal == 1` and `teamId ≠ 0`; held-out validation events: `actionType == "Turnover"`.
- Game-id map: the raw file stem ↔ 10-digit `gameId` map is a column of `results/clock_alignment_v1.csv`.

## Method lineage (credited)
- `ismayc/tracking-study`, commit `d21f8e3c3e7f90c7a9fe16554eafe503565757e2`: nearest-player-to-ball possession labels (≤ 4 ft, ball height ≤ 10 ft); for each play-by-play event at clock `c` and candidate lead ℓ, the majority label over tracking frames with `game_clock ∈ [c + ℓ, c + ℓ + 2.0]` (≥ 5 frames); the per-game lead is the argmax of shot-team agreement over ℓ ∈ {0, 0.5, …, 8.0} s; turnovers are held out. Our engine (`src/clock_latency_calibration.py`) reproduces the source's ten games exactly at the source's leads (8/10 identical leads; the two others differ by ≤ 1 labelled event through the source's non-deterministic tie-break; `docs/validation/EXTERNAL_REPLICATION.md`).
- Sign convention (unit-tested): `tracking_clock = pbp_clock + lead`; lead > 0 means the play-by-play stamp lags the tracking clock.

## Shipped tables
- `results/clock_alignment_v1.csv` — 632 rows (one per raw file): calibrated lead, lead status (CLOCK_CALIBRATION_VALIDATED / AMBIGUOUS_LEAD / DRIFTING_LEAD / HOLDOUT_FAIL / NO_TRACKING_MOMENTS), naive and calibrated shot/turnover agreement counts, first/second-half leads, plateau width, rising-edge lead, the 17-point agreement curve; sha256 in `results/clock_alignment_v1_manifest.json`.
- `results/taxonomy_by_game.csv` — the frozen curve-shape taxonomy (SHARP_UNIMODAL / FLAT_PLATEAU / MULTIMODAL / DRIFTING / INSUFFICIENT) per game (`configs/CURVE_TAXONOMY.yaml`).
- `results/global_shift_by_game.csv` — per-game held-out turnover and shot agreement at 0 s, +4 s and the per-game lead.
- Aggregates: `global_shift_summary.json`, `global_shift_screens.json`, `temporal_semantic_2x2.json`, `consequence_metrics.json`, `external_artifact_generalization.csv`, `full_season_table.csv`, `taxonomy_summary.csv`, `strata_descriptive.csv`, live-play `prevalence_*`, `distortion_*`, `segments_summary.json`, `universe_games.csv`, `fresh_clone_summary.json`, `failure_mode_examples.json`.
- `MANIFEST.sha256.json` — source map and sha256 of every shipped file.

Nothing in this repository is a re-timed or corrected copy of the tracking corpus.
