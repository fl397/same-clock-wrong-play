#!/usr/bin/env python3
"""prevalence of semantic classes / non-live frames (descriptive; no metric comparison).
Reads data/segments_semantic.parquet, data/frames_class_counts.parquet. Writes results/prevalence_*.csv, audit/PREVALENCE.md.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]
NONLIVE = {"TIMEOUT", "FREE_THROW_ADMINISTRATION", "SUBSTITUTION_OR_ADMINISTRATION", "OUT_OF_BOUNDS_OR_INBOUND_SETUP", "MADE_BASKET_DEAD_BALL"}
ORDER = ["LIVE_CONTINUOUS_PLAY", "FREE_THROW_ADMINISTRATION", "TIMEOUT", "SUBSTITUTION_OR_ADMINISTRATION", "MADE_BASKET_DEAD_BALL", "OUT_OF_BOUNDS_OR_INBOUND_SETUP", "PERIOD_BOUNDARY", "SEGMENTATION_ARTIFACT", "AMBIGUOUS"]


def main() -> int:
    s = pd.read_parquet(R / "data" / "segments_semantic.parquet"); fc = pd.read_parquet(R / "data" / "frames_class_counts.parquet")
    n_games, n_seg = s.game_id.nunique(), len(s)
    # --- class table: segments, frames (naive), nominal interval duration
    s["n_nonlive"] = s.n_frames_naive - s.n_frames_live
    cls = s.groupby("interval_class").agg(segments=("possession_id", "size"), frames=("n_frames_naive", "sum"), live_frames=("n_frames_live", "sum"), nominal_s=("interval_s", lambda x: x.clip(lower=0).sum())).reindex(ORDER).fillna(0)
    cls["segment_share"] = cls.segments / n_seg; cls["frame_share"] = cls.frames / cls.frames.sum(); cls["nominal_duration_share"] = cls.nominal_s / cls.nominal_s.sum()
    cls["nonlive_frame_share_within_class"] = 1 - cls.live_frames / cls.frames.replace(0, np.nan)
    cls.to_csv(R / "results" / "prevalence_by_class.csv")
    # --- corpus frame view (all deduplicated frames of the games, whatever segment)
    tot = fc[[c for c in fc.columns if c.startswith("game_frames_")]].sum(); frame_reasons = {k.replace("game_frames_", ""): int(v) for k, v in tot.items()}
    corpus_nonlive = 1 - frame_reasons["LIVE"] / frame_reasons["total"]
    # --- interval-level non-live
    inseg = s[s.n_frames_naive > 0]
    seg_nonlive_frac = inseg.n_nonlive.sum() / inseg.n_frames_naive.sum()
    any_nl = (inseg.n_nonlive > 0).mean(); g10 = ((inseg.n_nonlive / inseg.n_frames_naive) > 0.10).mean(); g25 = ((inseg.n_nonlive / inseg.n_frames_naive) > 0.25).mean(); g50 = ((inseg.n_nonlive / inseg.n_frames_naive) > 0.50).mean()
    ambiguous_frac = (s.interval_class == "AMBIGUOUS").mean(); no_tracking = (s.ambiguous_reason == "no_tracking").sum()
    # --- zero-span hypothesis test
    z = s[s.row_span_s == 0]; rz = z.row_span_class.value_counts(); rz_share = (rz / len(z)).round(4)
    zero_live_interval = (z.n_frames_live >= 25).mean()
    zero_row_stopped_frames = int(z.n_row_span_stopped.sum()); zero_row_frames = int(z.n_row_span_frames.sum())
    # --- breakouts (descriptive)
    s["late_game"] = (s.period == 4) & (s.end_clock <= 120)
    def brk(col):
        g = s[s.n_frames_naive > 0].groupby(col).agg(segments=("possession_id", "size"), nonlive_frame_share=("n_nonlive", "sum"), frames=("n_frames_naive", "sum"), live_class_share=("interval_class", lambda x: (x == "LIVE_CONTINUOUS_PLAY").mean()))
        g["nonlive_frame_share"] = g.nonlive_frame_share / g.frames; return g
    b = {"period": brk("period"), "late_game": brk("late_game"), "follows_made_basket": brk("follows_made_basket"), "has_free_throw": brk("has_free_throw"), "has_timeout": brk("has_timeout"), "has_oob_or_violation": brk("has_oob_or_violation")}
    pd.concat({k: v for k, v in b.items()}, names=["breakout", "level"]).to_csv(R / "results" / "prevalence_breakouts.csv")
    out = {"n_games": int(n_games), "n_segments": int(n_seg), "frame_reasons_corpus": frame_reasons, "corpus_nonlive_frame_share": corpus_nonlive,
           "segment_nonlive_frame_share": float(seg_nonlive_frac), "segments_with_any_nonlive": float(any_nl), "segments_gt10": float(g10), "segments_gt25": float(g25), "segments_gt50": float(g50),
           "ambiguous_segment_share": float(ambiguous_frac), "ambiguous_no_tracking_n": int(no_tracking), "zero_span_rows": int(len(z)), "zero_span_row_classes": rz.to_dict(), "zero_span_row_class_share": rz_share.to_dict(),
           "zero_span_rows_with_live_interval_ge25": float(zero_live_interval), "zero_span_row_span_frames": zero_row_frames, "zero_span_row_span_stopped_frames": zero_row_stopped_frames,
           "class_table": cls.reset_index().to_dict("records")}
    json.dump(out, open(R / "results" / "prevalence_summary.json", "w"), indent=2, default=float)
    md = ["# Prevalence — semantic classes and non-live tracking frames (descriptive)", "",
          f"Universe: {n_games} games (v3 ∩ SportVU ∩ CLOCK_CALIBRATION_VALIDATED), {n_seg:,} v3 possession rows → possession intervals. Classifier v1 frozen before the results were computed; no rule was changed after results.", "",
          "## Segment classes", "", "| class | segments | share | frames (naive) | frame share | nominal-duration share | non-live frame share within class |", "|---|---|---|---|---|---|---|"]
    md += [f"| {r.interval_class} | {int(r.segments):,} | {r.segment_share:.3f} | {int(r.frames):,} | {r.frame_share:.3f} | {r.nominal_duration_share:.3f} | {r.nonlive_frame_share_within_class:.3f} |" for r in cls.reset_index().itertuples()]
    md += ["", f"Ambiguous share {ambiguous_frac:.3f} (of which {no_tracking:,} have no tracking frames in the interval). SEGMENTATION_ARTIFACT = interval length ≤ 0 (two terminal stamps at the same second) or a row escaping its interval.", "",
           "## Frame-level prevalence", "", f"- Corpus (all deduplicated frames of the {n_games} games): {frame_reasons}; **non-live share = {corpus_nonlive:.3f}**.",
           f"- Inside possession intervals: non-live frames = **{seg_nonlive_frac:.3f}** of interval frames; intervals containing any non-live frame **{any_nl:.3f}**; > 10 % non-live {g10:.3f}; > 25 % {g25:.3f}; > 50 % {g50:.3f}.", "",
           "## Zero-span row hypothesis (H0: zero-span v3 row = dead ball)", "",
           f"{len(z):,} zero-span rows in the universe. Row-span classes: " + ", ".join(f"{k} {v} ({rz_share[k]:.3f})" for k, v in rz.items()) + ".",
           f"Fraction of zero-span rows whose possession interval contains ≥ 25 live frames: **{zero_live_interval:.3f}**. Under the frozen chains' closed row-span mask these rows yield {zero_row_frames:,} frames, of which {zero_row_stopped_frames:,} are stopped-clock.",
           "Reading: a zero-span row is a single-event possession whose row does not span its own play; H0 is rejected for the ZERO_CLOCK_SPAN_BUT_TRACKING_MOVEMENT share and the row-span mask, not the possession, is what selects dead-ball frames.", "",
           "## Descriptive breakouts (non-live frame share of interval frames; LIVE_CONTINUOUS_PLAY class share)", ""]
    for k, v in b.items():
        md += [f"### by {k}", "", "| level | segments | non-live frame share | live-class share |", "|---|---|---|---|"] + [f"| {i} | {int(r.segments):,} | {r.nonlive_frame_share:.3f} | {r.live_class_share:.3f} |" for i, r in v.iterrows()] + [""]
    (R / "audit" / "PREVALENCE.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "class_table"}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
