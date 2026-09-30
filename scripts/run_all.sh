#!/usr/bin/env bash
# Reproduction path for "Same Clock, Wrong Play" (user-supplied-source stage).
# Nothing in this repository downloads third-party data. Obtain the inputs yourself (docs/PROVENANCE.md), then point the
# environment variables below at them. Every producer is deterministic; all numbers in the abstract were produced by these stages.
set -euo pipefail
cd "$(dirname "$0")/.."

# ---- STAGE 0: inputs you supply (not redistributed here) -----------------------------------------------------------
export SPORTVU_JSON_DIR="${SPORTVU_JSON_DIR:-data/external/sportvu/json}"          # 632 raw game JSON files, public linouk23 mirror (2015-16)
export PBP_PARQUET="${PBP_PARQUET:-data/external/pbp/2015-16/all.parquet}"           # stats.nba.com PlayByPlayV3 rows for 2015-16, one parquet (columns listed in docs/PROVENANCE.md)
export BASKETBALL_RAW_ROOT="${BASKETBALL_RAW_ROOT:-data/external}"
mkdir -p data/derived results audit

# ---- STAGE 1: per-game calibration engine (source-exact reproduction of ismayc/tracking-study) --------------------------
# ingest -> (period, game_clock, player) de-duplication -> nearest-player possession labels -> shot-team agreement over a
# 0-8 s lead grid -> per-game lead -> held-out turnover agreement -> halves -> eventId diagnostic.  ~7 s/game single-threaded.
python3 src/clock_latency_calibration.py --self-test --out-dir data/derived/selftest
python3 src/clock_latency_calibration.py --json-dir "$SPORTVU_JSON_DIR" --pbp "$PBP_PARQUET" --out-dir audit/latency_all_games --resume
python3 src/aggregate_clock_latency.py            # -> audit/PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.csv (per-game lead, quality classes; lineage of results/clock_alignment_v1.csv)

# ---- STAGE 2: full-season characterization and curve taxonomy (reads only the per-game scalar table) -------------------
python3 src/characterize_full_season.py           # -> results/full_season_table.csv, taxonomy_by_game.csv, taxonomy_summary.csv

# ---- STAGE 3: global +4 s vs per-game calibration on held-out turnovers; wrong-team rates ------------------------------
python3 src/global_shift.py --stage events        # -> per-game turnover/shot agreement at 0 s, +4 s, per-game lead (cache in data/)
# python3 src/global_shift.py --stage screens     # needs withheld screen tables (SCREEN_PROJECT_DIR)
python3 src/global_shift.py --stage report        # -> results/global_shift_summary.json, results/global_shift_by_game.csv, audit/GLOBAL_SHIFT_BASELINE.md
#   The screen-consequence block of global_shift.py and consequence_metrics.py additionally needs screen-detection and
#   possession-inventory tables that are NOT redistributed (set SCREEN_PROJECT_DIR, V3_DIR, NPZ_DIR); see docs/REPRODUCIBILITY.md.

# ---- STAGE 4: temporal x semantic 2x2 (needs the possession-interval table V3_POSSESSIONS_PARQUET; see docs/REPRODUCIBILITY.md)
# python3 src/build_segments.py && python3 src/temporal_semantic_2x2.py   # -> results/temporal_semantic_2x2.json

# ---- STAGE 5: the two figures, from aggregates only --------------------------------------------------------------
ALIGNMENT_EFG_TABLE=results/external_artifact_generalization.csv ALIGNMENT_FIGURE_DIR=figures python3 src/figures_final.py

# ---- Deterministic 25-game subset check against the shipped tables ----------------------------------------------------------
# python3 src/fresh_clone_subset.py --json-dir "$SPORTVU_JSON_DIR" --pbp "$PBP_PARQUET" --out data/derived/fresh_clone_subset --reference .
echo "done"
