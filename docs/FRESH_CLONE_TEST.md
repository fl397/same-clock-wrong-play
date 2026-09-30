# Fresh-clone reproduction test

Fresh-clone verification performed on 2026-09-30 against commit `5ca905e` of this repository. The repository was cloned into an empty directory and every command below was run from that clone; nothing was copied in from the authors' working tree.

Environment: Linux; Python 3.12.13; numpy 2.2.6; pandas 2.2.3; scipy 1.13.1; statsmodels 0.14.4; matplotlib 3.10.8; CPU only.

## Level 1 — from the shipped aggregates (no external data)

```
git clone <repository url> same-clock-wrong-play && cd same-clock-wrong-play
pip install -r requirements.txt
python3 tests/test_smoke.py
```

Runtime 2.5 s. Result: **PASS**.

- Both figures were regenerated into `tests/_out/` and are byte-identical to the shipped files: `FIG1_naive_vs_corrected_spacing_efg.png` sha256 `57babd7fcc1a7a0e…`, `FIG2_measurement_resource_evidence.png` sha256 `e5e50d7cd46ee116…`.
- Every reported number was asserted against the shipped aggregates: held-out turnover-team agreement 0.393 (naive) / 0.942 (+4 s) / 0.932 (game-specific) over 16,943 turnovers and 631 games; pre-shot wrong-team share 0.690 → 0.035; 7,625 detected screens with onsets < 0.5 s falling 27.7 % → 4.7 % and 23.0 % reassigned; speed cancellation +0.22 / −0.20 / +0.03 SD; eFG by spacing quartile 0.478 → 0.572 under the naive join versus 0.524 / 0.498 / 0.491 / 0.505 corrected; taxonomy shares MULTIMODAL 19.0 %, DRIFTING 10.6 %; non-live frame share 14.7 %; the per-game table carries 632 rows.
- `MANIFEST.sha256.json` verified in the clone: 93 files, 0 hash mismatches.

## Level 2 — from user-supplied public sources (deterministic 25-game subset)

```
export SPORTVU_JSON_DIR=<directory with the 632 public mirror JSON files>
export PBP_PARQUET=<PlayByPlayV3 parquet for 2015-16>
export BASKETBALL_RAW_ROOT=<parent of the raw inputs>
python3 src/fresh_clone_subset.py --json-dir "$SPORTVU_JSON_DIR" --pbp "$PBP_PARQUET" \
        --out data/derived/fresh_clone_subset --reference .
```

Runtime 336 s for the 25 games with the smallest `sha256(game_id)`. The pipeline ran entirely from the clone's own code: raw ingest → `(period, game_clock, player)` de-duplication → nearest-player possession labels → shot-team agreement over the 0–8 s lead grid → per-game lead → held-out turnover agreement → quality flags → curve taxonomy → shot and turnover wrong-team rates at 0 s, +4 s and the per-game lead.

Agreement with the shipped tables: leads identical 25/25; quality status identical 25/25; taxonomy class identical 25/25; maximum absolute difference in shot-agreement rate 1.1e-16 and in turnover-agreement rate 1.1e-16; +4 s event counts identical 25/25. Subset composition: 16 plateau, 4 sharp-unimodal, 3 multimodal, 2 drifting.

One usability note: `src/fresh_clone_subset.py` reads the input locations from `SPORTVU_JSON_DIR` and `PBP_PARQUET` rather than from the command-line arguments alone, so the environment variables documented in `scripts/run_all.sh` must be set even when the flags are given.

## Boundary of what a clone can reproduce

- **Without any withheld file:** every number in the abstract and both figures (Level 1); the full calibration → validation → taxonomy → wrong-team chain on 25 games from the public inputs (Level 2). The same chain over all 632 games is `scripts/run_all.sh` stages 1–3, about 7 s per game single-threaded.
- **Requires intermediates that are not redistributed** (reconstruction documented in `docs/REPRODUCIBILITY.md`): the screen-based consequences (23.0 % reassigned, onsets < 0.5 s) need the detected-screen and possession-inventory tables; the temporal × semantic design (speed cancellation) needs the possession-interval table; the matched-shot audit needs the per-shot spacing cache, which `src/external_artifact_generalization.py` rebuilds from the public inputs.
- Classification: the code is reproducible; input access is manual; results are reproducible from user-supplied sources. Data-redistribution status is described in `docs/DATA_AVAILABILITY.md`.
