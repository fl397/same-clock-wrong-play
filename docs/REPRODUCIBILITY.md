# Reproducibility

Every number in the abstract maps to a producer in `src/` and an artifact in `results/`. Producers are deterministic (no random seeds are used in the alignment stages). Environment: Python 3.12.13 with the pins in `requirements.txt`.

## Level 1 — from the shipped aggregates (seconds, no external data)
```
pip install -r requirements.txt
python3 tests/test_smoke.py
```
Regenerates both figures into `tests/_out/` from `results/` and asserts: held-out turnover agreement 0.393 / 0.942 / 0.932; pre-shot wrong-team 69.0 % → 3.5 %; screen onsets 27.7 % → 4.7 %; the 2×2 speed cells and their SD differences (+0.22 / −0.20 / +0.03 SD); the eFG quartile values; taxonomy shares 19.0 % / 10.6 %.

## Level 2 — from the public sources (user-supplied)
Boundary: **INPUT_ACCESS_MANUAL.** Nothing here downloads third-party data. Obtain (a) the 632 raw 2015-16 SportVU game JSON files from the public linouk23 mirror and (b) the 2015-16 PlayByPlayV3 rows from stats.nba.com (via `nba_api`; column list in `docs/PROVENANCE.md`), then run `scripts/run_all.sh` with `SPORTVU_JSON_DIR` and `PBP_PARQUET` set.

| stage | producer | inputs | outputs | needs withheld intermediates? |
|---|---|---|---|---|
| 1 ingest → de-dup → per-game shot calibration → held-out turnover validation | `clock_latency_calibration.py`, `aggregate_clock_latency.py` | raw JSON + PBP | `audit/latency_all_games/games/*.json`, `audit/PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.csv` | no |
| 2 full-season characterization, curve taxonomy | `characterize_full_season.py` | per-game table | `results/full_season_table.csv`, `taxonomy_by_game.csv`, `taxonomy_summary.csv` | no |
| 3 global +4 s vs per-game vs naive on held-out turnovers; wrong-team rates | `global_shift.py --stage events/report` | raw JSON + PBP + per-game table | `results/global_shift_summary.json`, `global_shift_by_game.csv` | no |
| 3b screen reassignment / onset artefact | `global_shift.py --stage screens`, `consequence_metrics.py` | + screen detections, possession inventory | `results/global_shift_screens.json`, `consequence_metrics.json` | **yes** (`SCREEN_PROJECT_DIR`, `V3_DIR`, `NPZ_DIR`) |
| 4 temporal × semantic 2×2 | `build_segments.py`, `temporal_semantic_2x2.py` | + possession-interval table | `results/temporal_semantic_2x2.json` | **yes** (`V3_POSSESSIONS_PARQUET`, `PBP_WITH_CLOCK_PARQUET`) |
| 4b eFG/3PA by spacing quartile (external-artifact generalization) | `external_artifact_generalization.py` | + de-duplicated frame layer | `results/external_artifact_generalization.csv` | **yes** (`NPZ_DIR`) |
| 5 figures | `figures_final.py` | `results/` | `figures/` | no |
| check 25-game subset vs shipped tables | `fresh_clone_subset.py` | raw JSON + PBP | agreement report | no |

The withheld intermediates are derived from the same two public sources by the producers included here (`build_segments.py` builds possession intervals from PBP; the frame layer and screen detections come from companion projects whose producers are documented in `docs/validation/`); rebuilding them is possible but not packaged as a one-command path in this release. Classification of the overall path: **CODE_REPRODUCIBLE; INPUT_ACCESS_MANUAL; RESULT_REPRODUCIBLE_FROM_USER_SUPPLIED_SOURCE** for stages 1–3 and 5; stages 3b/4/4b additionally require rebuilding withheld intermediates.

## Recorded fresh-clone test
A clean clone was tested on a deterministic 25-game subset (the 25 smallest `sha256(game_id)`): leads, quality statuses, taxonomy classes and agreement rates matched the shipped tables exactly (25/25; rates to 1e-16); runtime 312.5 s (`docs/FRESH_CLONE_TEST.md`).
