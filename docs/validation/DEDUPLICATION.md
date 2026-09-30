# SportVU de-duplication audit

Question: raw SportVU event containers overlap (the same moment is shipped inside several consecutive containers). Do duplicated frames survive into (a) the Screen-detection frame tables, (b) the Timeout PFV/TSS chain, (c) the clock-latency calibration engine?

## Census (632 raw files; the per-game inventory produced by `src/sportvu_inventory.py`)
| quantity | median | min | max |
|---|---|---|---|
| raw moments per game | 209078 | 141963 | 296265 |
| unique (period, utc_ms) moments | 81439 | 60613 | 115694 |
| **duplication factor** raw / unique-utc | 2.571 | 2.140 | 3.241 |
| unique (period, game_clock) moments | 69986 | 51046 | 95633 |
| clock-collapse factor unique-utc / unique-clock (stopped-clock frames, NOT duplicates) | 1.171 | 1.076 | 1.272 |
| npz frames / unique-utc moments (v2 layer retention) | 0.892 | 0.616 | 0.974 |

Every game duplicates raw moments ≈ 2.6×. A second, distinct phenomenon is stopped-clock frames: ≈ 17 % more unique-utc moments than unique-clock values, i.e. frames recorded while the game clock is stopped (dead ball, free throws). Those are real frames, not duplicates; any producer that de-duplicates on `game_clock` collapses them.

## Where each layer de-duplicates
| layer | producer | key | keeps | duplicates survive? |
|---|---|---|---|---|
| v2 npz possession layer (input to Screen AND Timeout frames) | the possession extractor of the tracking pipeline — "Global dedup: (period, ts_ms) → first event_id that owned it"; 11-entity moments only; then per-event single-period / duration / min-frame filters | `(period, utc_ms)` | first container that carried the moment | **NO.** Verified two ways: (i) code path — a global `first_owner` dict guarantees one owner per key; (ii) direct re-execution on the 3 games with the most inter-possession wall-clock interval overlap: unique 11-entity keys = kept moments (66,947 / 60,438 / 61,366), each owned once. The v2 filters then drop ≈ 11 % of unique moments (retention 0.885 median) — a coverage loss, not a duplication. 63 games have ≤ 2 stored possessions whose [start_ts, end_ts] intervals overlap; these are non-contiguous kept moments of one container, not shared frames. |
| Screen-detection frame table | `the screen-detection frame builder` | `(period, clock)` keep-first in window order, on top of the npz | one frame per clock value | **NO** (already unique on utc); additionally collapses stopped-clock frames inside the npz (over-collapse ≈ 17 % of frames, essentially all in dead-ball segments outside live possessions). Every Screen v3 artifact (`v3_possession_inventory`, `screens_v3`, geometry features, context/response frames) descends from this table. |
| Timeout PFV / TSS | the possession-feature producers of the timeout-window study — concatenates frames of every linked npz possession whose `game_clock` falls in the v3 interval | none of its own | all npz frames in the clock mask | **NO.** Because each unique-utc moment lives in exactly one npz possession, concatenating several linked npz possessions cannot repeat a frame. Stopped-clock frames are kept (correct: they are distinct instants). The TSS chain (`run_tss_metric_sensitivity.py`) consumes PFV rows only. |
| Visual-audit clips | the visual-audit clip builder of the timeout-window study | same mask as PFV | same | **NO** |
| Clock-latency engine | `src/clock_latency_calibration.py::frames_from_events` | `(period, game_clock, player_id)` keep-first — the external source's key, reproduced exactly | one entity row per clock value | **NO**; stopped-clock frames collapsed, as in the source (irrelevant to calibration, which only labels live-ball windows). |

## Verdict
**No duplicated frames survive into Screen or Timeout.** The (period, utc_ms) global de-duplication in the v2 layer removes the container overlap before any downstream producer sees a frame. The failure condition ("duplicated frames survive downstream") is **not met**.

Two further non-duplication observations: (1) the v2 possession filters drop ≈ 11 % of unique moments per game (retention 0.62–0.97), which is the coverage loss behind Screen `C_TRACKING_GAP_OR_MISSING_FRAME` and Timeout `insufficient_frames` exclusions; (2) Screen's `game_frames` (period, clock) key collapses stopped-clock frames while Timeout keeps them — a harmless inconsistency inside possessions (the clock runs during live play) but one that should be unified when the context extraction is rebuilt on the calibrated axis.

Supporting per-game counts of overlapping stored-possession wall-clock intervals are regenerated into `audit/` by the de-duplication stage.
