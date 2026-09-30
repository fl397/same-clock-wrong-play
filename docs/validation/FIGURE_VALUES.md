# Figure values: each plotted quantity against its source artifact

Producer: `src/figures_final.py` (reads persisted results only; no tracking data; nothing recomputed). Outputs in `figures/`: `FIG1_naive_vs_corrected_spacing_efg.{pdf,png}`, `FIG2_measurement_resource_evidence.{pdf,png}` (PNG 300 dpi), sidecar `*.caption.txt`, and `plotted_values.json` (every plotted number as written by the producer). Captions are self-contained; no plotted claim exceeds the abstract.

## Figure 1 — analytical consequence (naive vs corrected spacing/eFG)
Source artifact: `results/external_artifact_generalization.csv` (producer `src/external_artifact_generalization.py`).

| element | plotted value | artifact value | match |
|---|---|---|---|
| naive eFG Q1–Q4 | 47.8 / 52.7 / 54.4 / 57.2 % | 0.4779 / 0.5267 / 0.5443 / 0.5718 | ✓ |
| corrected eFG Q1–Q4 | 52.4 / 49.8 / 49.1 / 50.5 % | 0.5243 / 0.4977 / 0.4910 / 0.5055 | ✓ |
| naive 3PA share Q1–Q4 | 16.8 / 18.9 / 21.5 / 30.5 % | 0.1685 / 0.1885 / 0.2154 / 0.3052 | ✓ |
| corrected 3PA share Q1–Q4 | 24.6 / 26.3 / 29.1 / 33.6 % | 0.2458 / 0.2626 / 0.2915 / 0.3357 | ✓ |
| naive shots | 27,563 | 6,891 + 6,890 + 6,891 + 6,891 | ✓ |
| corrected shots | 64,764 | 4 × 16,191 | ✓ |
| games | 437 validated (caption) | `docs/validation/SPACING_EFG_COMPARISON.md` | ✓ |

Caption (sidecar `FIG1_naive_vs_corrected_spacing_efg.caption.txt`) credits ismayc/tracking-study for the phenomenon and the 10-game eFG example and states that this figure is the season-scale generalization. Note for the full paper: the corrected axis in this table is the per-game lead (the artifact as produced); the fixed +4 s shift performed at least as well on held-out turnovers. Axis language: "Offensive-spacing quartile (five-player convex-hull area, 2-s window at the shot)"; units are percentages.

## Figure 2 — measurement / resource evidence
Sources: `results/global_shift_by_game.csv`, `results/global_shift_summary.json` (producer `src/global_shift.py`), `results/global_shift_screens.json`, `results/temporal_semantic_2x2.json` (producer `src/temporal_semantic_2x2.py`).

| element | plotted value | artifact value | match |
|---|---|---|---|
| A: pooled held-out agreement naive / +4 s / per-game | 0.393 / 0.942 / 0.932 | 0.3931 / 0.9419 / 0.9319 (`universe.all_calibratable`) | ✓ |
| A: ECDF sample | 631 games | `n_games` 631; per-game `to_rate_M0/M1/M2` | ✓ |
| A: held-out turnovers (caption) | 16,943 | `M0.n_events` 16943 | ✓ |
| B: pre-shot window wrong team | 69.0 % → 3.5 % | 0.6899 → 0.0353 | ✓ |
| B: pre-turnover window wrong team | 60.7 % → 5.8 % | 0.6069 → 0.0581 | ✓ |
| B: screen onset < 0.5 s | 27.7 % → 4.7 % | 0.2770 → 0.0474 (7,625 screens, 301 games) | ✓ |
| C: mean speed cells A/B/C/D | 6.97 / 7.30 / 6.63 / 6.92 ft/s | 6.9738 / 7.3013 / 6.6268 / 6.9194 | ✓ |
| C: A−C | +0.35 ft/s (+0.22 SD) | +0.3471 ft/s; +0.2154 SD of cell D (sd 1.6112) | ✓ |
| C: A−B | −0.33 ft/s (−0.20 SD) | −0.3275 ft/s; −0.2033 SD | ✓ |
| C: A−D | +0.05 ft/s (+0.03 SD) | +0.0544 ft/s; +0.0338 SD | ✓ |
| C: possessions (caption) | 56,033 | `n_paired_all_cells` 56033 (301 games) | ✓ |

CI meaning: Figure 2 shows no confidence intervals; agreement rates are exact event proportions, and the per-game ECDF conveys dispersion (stated in the caption). Abbreviations are expanded in the captions (eFG, 3PA, SD, play-by-play). Readability: 300-dpi PNG plus vector PDF; smallest font ≈ 7.8 pt at 15.5 × 4.8 in.

## After the final presentation edit (2026-09-21)
Figure 1 was re-rendered by the same producer (`src/figures_final.py`, presentation-only edit) from the same artifact (`external_artifact_generalization.csv`, the spacing/eFG comparison):
- the three-point-share panel (former panel B) was **REMOVED** — the figure communicates one fact, that the apparent spacing–eFG gradient disappears after clock correction; the 3PA rows above are no longer plotted (values kept for the record only, not interpreted);
- x-axis label shortened to "Offensive-spacing quartile"; the hull-area definition moved to the caption (the colliding-label defect is gone);
- title: "Clock alignment removes the apparent spacing–efficiency gradient";
- caption rewritten without the forbidden shot-selection clause; ismayc credit retained.
Plotted eFG values unchanged (`figures/plotted_values.json`: naive 0.4779/0.5267/0.5443/0.5718; corrected 0.5243/0.4977/0.4910/0.5055; n 27,563 / 64,764). New hashes: PNG `57babd7fcc1a7a0e…` (1836 × 1223 px, 300 dpi), PDF `60cb13465a96ab2b…`. Figure 2 untouched: PNG `e5e50d7cd46ee116…` (4608 × 1426 px), PDF `34ba61b357094161…`. Full hashes: `figures/final_lock_hashes.json`.

## After the public-release presentation pass (2026-09-30)

Both figures were re-rendered by the same producer (`src/figures_final.py`); no value was recomputed and no scientific
claim changed. Changes:

**Figure 1 — full-sample version.** Figure 1 plots the full eligible
samples so that it shows exactly the numbers quoted in the abstract: naive equal-clock join 27,563 shots, corrected join
64,764 shots (437 validated games), grouped bars, values from `results/external_artifact_generalization.csv`.

| element | plotted value | artifact value | match |
|---|---|---|---|
| naive shots | 27,563 | 6,891 + 6,890 + 6,891 + 6,891 | OK |
| corrected shots | 64,764 | 4 x 16,191 | OK |
| naive eFG Q1-Q4 | 47.8 / 52.7 / 54.4 / 57.2 % | 0.4779 / 0.5267 / 0.5443 / 0.5718 | OK |
| corrected eFG Q1-Q4 | 52.4 / 49.8 / 49.1 / 50.5 % | 0.5243 / 0.4977 / 0.4910 / 0.5055 | OK |

Hashes: PNG `57babd7fcc1a7a0eb0eec9a8fe5db6785edfe368ee2d1b2f20ced39ae6d32aab`, PDF `60cb13465a96ab2b572e8d3ad03d53af7ffa22363accd7ff7f86948420c1e2b2` (identical to the version audited before the
presentation pass; the producer regenerates the PNG byte-for-byte). The corrected series is described as **non-monotonic**,
never as flat or absent; interpretation limits in `docs/validation/FIGURE1_QUARTILE_NOTE.md`.

**Matched-shot comparison (supporting check, not the primary figure).** On the 26,177 shots common to both joins the
naive gradient is intact and monotone (48.5 / 53.2 / 54.7 / 57.7 %, Q4-Q1 +9.2 points) while the corrected series is
non-monotonic with Q4-Q1 +0.3 points (54.6 / 51.5 / 53.0 / 54.9 %); values in `results/matched_shot_audit.json`,
narrative in `docs/validation/MATCHED_SHOT_VALIDATION.md`. It shows that the primary comparison is not an artefact of the two
samples having different sizes.

**Figure 2 - panels B and C.** Panel B is retitled "B. Downstream state-assignment errors before / after the shift"
(the plotted quantities are wrong-team attribution for shots and turnovers and early screen onsets). Panel C no longer
draws the four cell means as bars on an axis starting at 6.0 ft/s; it plots the three paired differences on an axis that
includes zero - clock error +0.35 ft/s (+0.22 SD), non-live frames -0.33 ft/s (-0.20 SD), net +0.05 ft/s (+0.03 SD) -
with the four cell means (6.97 / 7.30 / 6.63 / 6.92 ft/s) retained in an annotation. All values are unchanged.

New hashes: Figure 1 PNG `453e1384566eabc9...` (1896 x 1283 px, 300 dpi), PDF `7aef6331379f1b98...`; Figure 2 PNG
`c487806549cd5894...` (4621 x 1426 px), PDF `4b2b1e291e62ef50...`. Full hashes in `figures/final_lock_hashes.json` and
`MANIFEST.sha256.json`. PNG hashes are the stable check: matplotlib embeds a creation timestamp in the PDF, so PDF
hashes change on every render.
