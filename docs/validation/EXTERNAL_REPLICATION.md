# Exact 10-game reproduction of the external latency calibration

Producer: `src/clock_latency_calibration.py` (sign-convention unit test `--self-test` PASSED).
Inputs: the 10 raw SportVU JSON files in `<DATA_ROOT>/raw/sportvu/json/` matching the source's 10 games; PBP = (run A) the source's own harvested PlayByPlayV3 files, (run B) our `raw/pbp/2015-16/all.parquet`.
Outputs: `audit/LATENCY_EXTERNAL_REPLICATION_10G.csv` (20 rows = 10 games × 2 PBP sources); per-game JSON with the full 17-point agreement curve, halves and eventId diagnostic in `audit/latency_replication_10g_{sourcepbp,ourpbp}/games/`.
Source reference: `output/possession_validation.csv` at commit `d21f8e3c` (see `docs/validation/EXTERNAL_SOURCE_METHOD.md`).

## Result: run A (source PBP) and run B (our PBP) are IDENTICAL on every column
The two PBP sources give the same leads, the same agree/n at every lead, and the same held-out turnover counts for all 10 games (row-wise equality check: True). The PBP endpoint is therefore not a source of difference.

## Per-game comparison (run B = our PBP; run A identical)
| game | game_id | source lead | our lead | Δ (0.5-s steps) | source shots agree/n | ours @ source lead | ours @ our lead | source TO agree/n | ours TO @ our lead | tie status | top-3 of our curve |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01.01.2016.ORL.at.WAS | 0021500490 | 4.0 | 4.0 | 0 | 175/177 (0.9887) | 175/177 (0.9887) | 175/177 (0.9887) | 24/24 (1.0000) | 24/24 (1.0000) | UNIQUE | 4.0:0.9887;3.5:0.9886;2.5:0.9830 |
| 01.01.2016.DAL.at.MIA | 0021500491 | 5.5 | 5.5 | 0 | 153/157 (0.9745) | 153/157 (0.9745) | 153/157 (0.9745) | 19/21 (0.9048) | 19/21 (0.9048) | UNIQUE | 5.5:0.9745;4.5:0.9684;5.0:0.9682 |
| 01.01.2016.CHA.at.TOR | 0021500492 | 6.0 | 6.0 | 0 | 167/172 (0.9709) | 167/172 (0.9709) | 167/172 (0.9709) | 20/22 (0.9091) | 20/22 (0.9091) | UNIQUE | 6.0:0.9709;5.5:0.9649;6.5:0.9649 |
| 01.01.2016.NYK.at.CHI | 0021500493 | 4.0 | 4.5 | 1 | 152/156 (0.9744) | 152/156 (0.9744) | 153/157 (0.9745) | 15/16 (0.9375) | 14/16 (0.8750) | UNIQUE | 4.5:0.9745;4.0:0.9744;3.0:0.9682 |
| 01.01.2016.PHI.at.LAL | 0021500494 | 5.5 | 5.5 | 0 | 156/161 (0.9689) | 156/161 (0.9689) | 156/161 (0.9689) | 21/24 (0.8750) | 21/24 (0.8750) | UNIQUE | 5.5:0.9689;4.5:0.9632;6.0:0.9632 |
| 01.02.2016.BKN.at.BOS | 0021500495 | 3.0 | 5.5 | 5 | 171/178 (0.9607) | 170/178 (0.9551) | 173/181 (0.9558) | 26/28 (0.9286) | 25/28 (0.8929) | UNIQUE | 5.5:0.9558;3.0:0.9551;6.0:0.9503 |
| 01.02.2016.DET.at.IND | 0021500498 | 2.5 | 2.5 | 0 | 149/149 (1.0000) | 149/149 (1.0000) | 149/149 (1.0000) | 19/21 (0.9048) | 19/21 (0.9048) | TIE_5_SMALLEST_CHOSEN | 2.5:1.0000;3.0:1.0000;3.5:1.0000 |
| 01.02.2016.HOU.at.SAS | 0021500502 | 4.0 | 4.0 | 0 | 123/126 (0.9762) | 123/126 (0.9762) | 123/126 (0.9762) | 21/23 (0.9130) | 21/23 (0.9130) | UNIQUE | 4.0:0.9762;4.5:0.9688;5.0:0.9685 |
| 01.02.2016.MEM.at.UTA | 0021500503 | 3.5 | 3.5 | 0 | 154/155 (0.9935) | 154/155 (0.9935) | 154/155 (0.9935) | 27/27 (1.0000) | 27/27 (1.0000) | UNIQUE | 3.5:0.9935;4.0:0.9871;3.0:0.9806 |
| 01.02.2016.DEN.at.GSW | 0021500504 | 5.0 | 5.0 | 0 | 183/191 (0.9581) | 183/191 (0.9581) | 183/191 (0.9581) | 26/26 (1.0000) | 26/26 (1.0000) | UNIQUE | 5.0:0.9581;4.5:0.9529;4.0:0.9424 |
## Pooled
| quantity | source (README / validation CSV) | ours at the source's leads | ours at our own leads |
|---|---|---|---|
| shots (calibration metric) | 1,583 / 1,622 = **97.60 %** | 1,582 / 1,622 = 97.53 % | 1,586 / 1,626 = 97.54 % |
| turnovers (held out) | 218 / 232 = **93.97 %** | — (not recomputed at the source's leads) | 216 / 232 = 93.10 % |
| naive join (lead 0) | 67 % over 10 games (README prose) | — | 32.3 % shots (labelled-event denominator), 38.9 % turnovers |

Note on the naive figure: the README's "67 %" samples "~1 s before" the event; our naive column is lead = 0.0 exactly with the labelled-event denominator, so the two are not the same statistic. Neither is used downstream.

## Reading
- **8 / 10 games**: identical lead, identical agree/n at every reported point, identical held-out turnover count.
- **NYK@CHI (0021500493)**: at the source's lead (4.0) our agree/n is identical to the source (152/156). Our curve has 153/157 at 4.5 (0.97452 > 0.97436), so strict-`>` argmax picks 4.5. The source must have scored ≤ 152/156-equivalent at 4.5; the difference is at most one labelled event and is attributable to the non-deterministic majority tie-break in the source's `window_label` (D3 in the source audit). Effect: 1 grid step (0.5 s), well inside the 2.0-s label window. Held-out turnovers 14/16 vs 15/16.
- **BKN@BOS (0021500495)**: at the source's lead (3.0) we score 170/178 vs the source's 171/178 — a one-event difference (same tie-break cause). The game's curve is **bimodal** (0.9551 at 3.0 vs 0.9558 at 5.5; 0.9503 at 6.0); the one-event difference flips the argmax from 3.0 to 5.5. Held-out turnovers 25/28 at 5.5 vs the source's 26/28 at 3.0. This game is flagged `BIMODAL_CURVE` for the all-game pass (a per-game lead whose top two peaks are ≥ 2 grid steps apart and within 1 event of each other is reported, not trusted blindly — the flag rule is stated in `PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.md`).
- **DET@IND (0021500498)**: 149/149 at five consecutive leads 2.5–4.5; both implementations choose the smallest (2.5) — identical by construction.

## Decision
LATENCY_IMPLEMENTATION_VALIDATION = **PASS**.
Criteria: leads identical in 8/10; the two non-identical games differ by ≤ 1 labelled shot event out of ≥ 156 at the source's lead, with the divergence mechanism identified (non-deterministic tie-break in the source, D3) and bounded; pooled shot agreement within 0.07 percentage points of the source; held-out turnover agreement within 2 events of 232. No material inconsistency. The BKN@BOS bimodality is carried forward as a documented failure mode of the per-game argmax, not as an implementation error.

The 10-game replication passed; the all-game calibration follows.
