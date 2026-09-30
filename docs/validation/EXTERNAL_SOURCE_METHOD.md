# External source implementation audit: PBP↔SportVU scorer-latency calibration

Purpose: recover the external method EXACTLY before applying it to our universe. No outcome quantity is read here.

## Source
| item | value |
|---|---|
| repository | https://github.com/ismayc/tracking-study |
| commit audited | `d21f8e3c3e7f90c7a9fe16554eafe503565757e2` (2026-09-05 14:08:29 −0700, "Regenerate figures: tooltips keep the player name, bars keep their labels") |
| local clone | a local clone of `tracking-study` (read-only; not copied into the repositories) |
| method file | `python/06_possession_join.py` sha256 `f7a73390e20cbccaf97d580c8dbe4ef908f1d76e7758bdea1b6ea733c5b0a292` |
| heuristic file | `python/03_analysis.py` sha256 `54a294f0ee65c7ba2ac7a30acdc315c22f8381ed902b6ceb79f20018fc33e207` (`possession_frames`) |
| moment parser | `python/02_parse_moments.py` sha256 `2ced1c78815a0aba570b9076d2c9f1c3c15d95e85e423419b5d8e33833a9ff01` |
| PBP harvester | `python/05_harvest_pbp.py` sha256 `c3602f07ada5e60c541aed730074084edf266cd9f126d860201573091fc26a17` (stats.nba.com `playbyplayv3`, the same endpoint as our `raw/pbp/2015-16/all.parquet`) |
| reported per-game results | `output/possession_validation.csv` sha256 `4d86075691b7a49114f0376dfc89c8e520b58e49ce0a85769f3f466d075afdf1` |
| README | sha256 `96f2d7b3a26f6ebbfe3e9d7a565bc0a9eec40b3fd482b3142a1f385526f86ac0` |
| SportVU input | linouk23 `NBA-Player-Movements` archive (same provenance as `<DATA_ROOT>/raw/sportvu/json/`) |

## The 10 games (source file stem → NBA game id → source lead)
| stem | game_id | source calibrated lead (s) |
|---|---|---|
| 01.01.2016.ORL.at.WAS | 0021500490 | 4.0 |
| 01.01.2016.DAL.at.MIA | 0021500491 | 5.5 |
| 01.01.2016.CHA.at.TOR | 0021500492 | 6.0 |
| 01.01.2016.NYK.at.CHI | 0021500493 | 4.0 |
| 01.01.2016.PHI.at.LAL | 0021500494 | 5.5 |
| 01.02.2016.BKN.at.BOS | 0021500495 | 3.0 |
| 01.02.2016.DET.at.IND | 0021500498 | 2.5 |
| 01.02.2016.HOU.at.SAS | 0021500502 | 4.0 |
| 01.02.2016.MEM.at.UTA | 0021500503 | 3.5 |
| 01.02.2016.DEN.at.GSW | 0021500504 | 5.0 |

## Method as implemented in code (authoritative; README prose is secondary)
1. **Moments** (`02_parse_moments.py`): every event container's moments are exploded to one row per entity; rows are de-duplicated on `(period, game_clock, player_id)` keep-first. Consequence: overlapping event containers are collapsed AND stopped-clock frames (same game_clock, different wall-clock) are collapsed to one frame. Ball is `player_id == -1`.
2. **Possession heuristic** (`03_analysis.py::possession_frames`): per frame, offense = team of the player nearest the ball, only if ball height ≤ 10.0 ft and nearest-player distance ≤ 4.0 ft (`POSSESSION_MAX_BALL_Z`, `POSSESSION_MAX_DIST`); frames failing either test carry no label.
3. **Label** (`06_possession_join.py::window_label`): for PBP event at `(period, clock)` and lead ℓ, take labelled frames with `game_clock ∈ [clock + ℓ, clock + ℓ + 2.0]` (`LOOKBACK_S = 2.0`); require ≥ 5 frames (`MIN_FRAMES = 5`); label = team with the most frames (polars `group_by…sort(n, descending)` → first row; ties are resolved by polars' output order, which is not guaranteed deterministic).
4. **Calibration** (`calibrate_lead`): grid ℓ ∈ {0.0, 0.5, …, 8.0} (`LEAD_GRID`, 17 values); metric = agreement between the label and the PBP `teamId` over **shots only** (`isFieldGoal == "1"`, `teamId ≠ 0`); events with no label (fewer than 5 frames) are excluded from the denominator; argmax uses strict `>` while iterating the grid upward → the **smallest** lead among exact ties.
5. **Held-out check**: turnovers (`actionType == "Turnover"`) scored at the calibrated lead; never used to choose ℓ.
6. **PBP clock**: `PT..M..S` parsed to seconds remaining in period (1-s resolution in the source data); tracking clock 0.01-s resolution.
7. **Sign convention** (implicit in code): `tracking_clock_target = pbp_clock + lead`. Because the period clock counts down, a positive lead points to an EARLIER real-time instant than the PBP stamp, i.e. **the PBP stamp lags the tracking clock by ℓ seconds** ("play-by-play clocks lag the tracking clock by a per-game scorer latency of 2.5–6.0 seconds", README). Frozen for our implementation in `src/clock_latency_calibration.py::tracking_clock_target` with a unit test (600.0 + 4.0 → 604.0; `--self-test` PASSED).

## Code / README discrepancies found
| # | item | finding |
|---|---|---|
| D1 | half-game drift sensitivity | README §"Robustness of the constant-latency assumption" (and `08_findings.py` prose) reports calibrating each half separately, "moves the chosen lead by up to 2.5 s in a few games, but agreement at either half's optimum stays between 94% and 100%". **No code in the repository computes this** (grep of `python/*.py` for a half split: none). It is prose only, not reproducible from the commit. Our implementation adds the half-game analysis explicitly (below) rather than inheriting a number. |
| D2 | pooled counts | README reports 97.6 % on 1,622 shots and 94.0 % on 232 turnovers; `output/possession_validation.csv` sums to 1,583/1,622 (97.60 %) and 218/232 (93.97 %). Consistent. |
| D3 | majority tie-break | `window_label` relies on polars group-by output order for exact ties; not deterministic by contract. Our implementation uses the first-seen team in the window (documented in code). This is the only identified source of ≤ 1-event differences (see `docs/validation/EXTERNAL_REPLICATION.md`). |
| D4 | de-duplication key | Source dedups on `(period, game_clock, player_id)`; our production layers use different keys (v2 npz: `(period, utc_ms)`; Screen `game_frames()`: `(period, clock)`). Documented in `docs/validation/DEDUPLICATION.md`. For the replication we use the source key exactly. |
| D5 | insufficient-event handling | Source has no minimum-event rule (10 hand-picked full games). Our all-game pass adds `INSUFFICIENT_CALIBRATION_EVENTS` (< 20 labelled shots) and `INSUFFICIENT_HOLDOUT_EVENTS` (< 5 turnovers) quality flags; flagged games are reported, never silently calibrated. |

## What we did NOT inherit
- No spacing / eFG / hull quantities; no modern-aggregate material.
- No source PBP files are used in production: our reproduction was run twice, once with the source's harvested PBP (a local copy of the harvested source play-by-play) and once with our `raw/pbp/2015-16/all.parquet`; results identical (see replication report).

The replication of this method on the source's 10 games is reported in `docs/validation/EXTERNAL_REPLICATION.md`.
