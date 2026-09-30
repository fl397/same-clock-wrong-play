# Per-game quality labels

`results/taxonomy_by_game.csv` gives one frozen label per game (rules in `configs/CURVE_TAXONOMY.yaml`, committed before the labels were computed; `docs/validation/CURVE_CLASSES.md`). `results/clock_alignment_v1.csv` carries the underlying per-game quantities (lead, plateau width, half-game leads, agreement counts, the full 17-point agreement curve).

| technical label (frozen) | operational reading | share of 632 games | held-out turnover agreement, fixed +4 s / game-specific |
|---|---|---|---|
| SHARP_UNIMODAL | NORMAL / HIGH-CONFIDENCE — one clear agreement peak | 22.5 % (142) | 0.944 / 0.935 |
| FLAT_PLATEAU | PLATEAU — the offset is identified only to a 2–3 s band; +4 s lies inside it | 47.8 % (302) | 0.943 / 0.932 |
| MULTIMODAL | MULTIMODAL — two agreement peaks within one labelled event; lower confidence | 19.0 % (120) | 0.944 / 0.939 |
| DRIFTING | DRIFTING — first- and second-half leads differ by more than 2 s; lowest confidence | 10.6 % (67) | 0.931 / 0.911 |
| INSUFFICIENT | no calibration possible (one game with zero tracking moments) | 0.2 % (1) | — |

**Explicit statement.** A fixed +4.0 s shift performs at least as well as game-specific calibration overall (0.942 vs 0.932 pooled) and within every class. The labels therefore communicate *how uncertain the offset is in a given game* — which games to treat as lower confidence, exclude from frame-precise analyses, or down-weight — not a recommendation to calibrate per game. The per-game leads are retained for transparency and as the input to the labels; +4.0 s is the recommended correction for this corpus.

**How to use.** Join by `game_id`; apply `tracking_clock = pbp_clock + 4.0` before selecting frames; if the label is MULTIMODAL or DRIFTING, treat event-anchored frame windows in that game as lower confidence (DRIFTING games retain ≈ 7 % wrong-team turnover windows even after correction); never re-tune the offset on a basketball outcome.

Scope: the public 2015-16 SportVU / PlayByPlayV3 corpus only.
