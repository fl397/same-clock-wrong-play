#!/usr/bin/env python3
"""M1/M2/M3 NAIVE vs LIVE_PLAY_ONLY distortion (possession / game / team-season), context dependence,
timeout-window structure only. Rules: configs/LIVE_PLAY_CLASSIFIER.yaml v1 (frozen before any comparison). No effect estimate.
Writes results/distortion_*.csv, results/distortion_summary.json, audit/DISTORTION.md.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import pearsonr, spearmanr, mannwhitneyu

R = Path(__file__).resolve().parents[1]
WIN = os.environ.get("TIMEOUT_WINDOWS_PARQUET", "data/derived/v3_timeout_windows.parquet")
M = ["M1", "M2", "M3"]; NAMES = {"M1": "player speed (ft/s)", "M2": "offensive spacing hull (sq ft)", "M3": "team dispersion (ft)"}
NONLIVE = {"TIMEOUT", "FREE_THROW_ADMINISTRATION", "SUBSTITUTION_OR_ADMINISTRATION", "OUT_OF_BOUNDS_OR_INBOUND_SETUP", "MADE_BASKET_DEAD_BALL"}


def paired(x: np.ndarray, y: np.ndarray) -> dict:
    d = x - y; ad = np.abs(d)
    return {"n_pairs": int(len(d)), "mean_naive": float(x.mean()), "mean_live": float(y.mean()), "paired_mean_diff_naive_minus_live": float(d.mean()),
            "standardized_diff": float(d.mean() / y.std(ddof=1)) if len(d) > 1 and y.std(ddof=1) > 0 else np.nan,
            "pearson": float(pearsonr(x, y)[0]) if len(d) > 2 else np.nan, "spearman": float(spearmanr(x, y)[0]) if len(d) > 2 else np.nan,
            "mae": float(ad.mean()), "p90_abs_change": float(np.quantile(ad, 0.9)), "median_abs_change": float(np.median(ad))}


def main() -> int:
    s = pd.read_parquet(R / "data" / "segments_semantic.parquet")
    rows, summ = [], {}
    # ---- possession level
    for m in M:
        both = s.dropna(subset=[f"naive_{m}", f"live_{m}"])
        r = paired(both[f"naive_{m}"].values, both[f"live_{m}"].values); r.update(level="possession", metric=m, n_naive_only=int((s[f"naive_{m}"].notna() & s[f"live_{m}"].isna()).sum()), n_naive_valued=int(s[f"naive_{m}"].notna().sum()), n_live_valued=int(s[f"live_{m}"].notna().sum()))
        rows.append(r)
    # ---- game (game, offense team) level
    g = s.groupby(["game_id", "offense_team_id"]).agg(**{f"naive_{m}": (f"naive_{m}", "mean") for m in M}, **{f"live_{m}": (f"live_{m}", "mean") for m in M}).reset_index()
    for m in M:
        both = g.dropna(subset=[f"naive_{m}", f"live_{m}"]); r = paired(both[f"naive_{m}"].values, both[f"live_{m}"].values); r.update(level="game_team", metric=m); rows.append(r)
    # ---- team-season level (possession-weighted mean over all possessions with a value in that condition)
    t = s.groupby("offense_team_id").agg(**{f"naive_{m}": (f"naive_{m}", "mean") for m in M}, **{f"live_{m}": (f"live_{m}", "mean") for m in M}, n_poss=("possession_id", "size"), n_live_valued=("live_M2", "count")).reset_index()
    team_rows = []
    for m in M:
        both = t.dropna(subset=[f"naive_{m}", f"live_{m}"]); x, y = both[f"naive_{m}"].values, both[f"live_{m}"].values
        rn = pd.Series(-x).rank(method="min").values; rl = pd.Series(-y).rank(method="min").values; shift = np.abs(rn - rl)
        r = paired(x, y); r.update(level="team_season", metric=m, n_teams=int(len(both)), rank_spearman=float(spearmanr(x, y)[0]), max_abs_rank_shift=int(shift.max()), median_abs_rank_shift=float(np.median(shift)), teams_with_rank_change=int((shift > 0).sum()))
        rows.append(r); team_rows.append(pd.DataFrame({"team_id": both.offense_team_id, "metric": m, "naive": x, "live": y, "rank_naive": rn, "rank_live": rl, "abs_rank_shift": shift}))
    pd.concat(team_rows).to_csv(R / "results" / "distortion_team_season_ranks.csv", index=False)
    D = pd.DataFrame(rows); D.to_csv(R / "results" / "distortion_stats.csv", index=False)
    # ---- context dependence
    s["absd_M1"] = (s.naive_M1 - s.live_M1).abs(); s["absd_M2"] = (s.naive_M2 - s.live_M2).abs(); s["absd_M3"] = (s.naive_M3 - s.live_M3).abs()
    clean = s[s.interval_class == "LIVE_CONTINUOUS_PLAY"]; nl = s[s.interval_class.isin(NONLIVE)]
    ctx = {}
    for m in M:
        a, b = clean[f"absd_{m}"].dropna(), nl[f"absd_{m}"].dropna()
        ctx[m] = {"clean_n": int(len(a)), "clean_median_abs_change": float(a.median()), "clean_p90": float(a.quantile(0.9)), "nonlive_n": int(len(b)), "nonlive_median_abs_change": float(b.median()), "nonlive_p90": float(b.quantile(0.9)),
                  "mannwhitney_p_two_sided": float(mannwhitneyu(a, b, alternative="two-sided").pvalue) if len(a) and len(b) else np.nan,
                  "nonlive_class_breakdown_median": {c: float(nl[nl.interval_class == c][f"absd_{m}"].median()) for c in sorted(NONLIVE)}}
    # ---- timeout windows, structure only
    w = pd.read_parquet(WIN); w["game_id"] = w.game_id.astype(str).str.zfill(10); w = w[w.game_id.isin(set(s.game_id))]
    cls = s.set_index("possession_id").interval_class; nn = s.set_index("possession_id").n_frames_naive; nlv = s.set_index("possession_id").n_frames_live; rs = s.set_index("possession_id").n_row_span_frames; rss = s.set_index("possession_id").n_row_span_stopped
    n_win = n_win_nl = n_mem = n_mem_nl = fr = fr_nl = rsf = rsf_st = 0
    for r in w.itertuples():
        ids = [p for col in ("pre_offense_possession_ids", "post_offense_possession_ids", "pre_defense_possession_ids", "post_defense_possession_ids") for p in json.loads(getattr(r, col))]
        ids = [p for p in ids if p in cls.index]
        if not ids:
            continue
        n_win += 1; c = cls.loc[ids]; n_mem += len(ids); k = int(c.isin(NONLIVE).sum()); n_mem_nl += k; n_win_nl += int(k > 0)
        fr += int(nn.loc[ids].sum()); fr_nl += int((nn.loc[ids] - nlv.loc[ids]).sum()); rsf += int(rs.loc[ids].sum()); rsf_st += int(rss.loc[ids].sum())
    case = {"windows_with_members_in_universe": n_win, "windows_with_any_nonlive_class_member": n_win_nl, "frac_windows_any_nonlive": n_win_nl / max(n_win, 1), "member_possessions": n_mem, "frac_members_nonlive_class": n_mem_nl / max(n_mem, 1),
            "member_interval_frames": fr, "frac_member_interval_frames_nonlive": fr_nl / max(fr, 1), "member_row_span_frames_frozen_chain": rsf, "frac_member_row_span_frames_stopped_clock": rsf_st / max(rsf, 1), "label": "structure only"}
    summ = {"possession_game_team_stats": rows, "context_dependence": ctx, "timeout_case_study": case, "classifier_freeze": "frozen before any comparison"}
    json.dump(summ, open(R / "results" / "distortion_summary.json", "w"), indent=2, default=float)
    # ---- report
    md = ["# Distortion of M1/M2/M3 under NAIVE_PBP_POSSESSION vs LIVE_PLAY_ONLY", "",
          f"Universe {s.game_id.nunique()} games, {len(s):,} segments; metrics and conditions frozen in `configs/LIVE_PLAY_CLASSIFIER.yaml` v1 (frozen before any comparison). Naive = all frames in (end+lead, prev_end+lead]; live-only = running-clock frames; a value needs ≥ 25 usable frames.", "",
          "| level | metric | n pairs | mean naive | mean live | paired Δ (naive − live) | standardized Δ | Pearson | Spearman | MAE | median |Δ| | p90 |Δ| | naive-only (no live value) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['level']} | {r['metric']} {NAMES[r['metric']]} | {r['n_pairs']:,} | {r['mean_naive']:.3f} | {r['mean_live']:.3f} | {r['paired_mean_diff_naive_minus_live']:+.3f} | {r['standardized_diff']:+.3f} | {r['pearson']:.3f} | {r['spearman']:.3f} | {r['mae']:.3f} | {r['median_abs_change']:.3f} | {r['p90_abs_change']:.3f} | {r.get('n_naive_only', '')} |")
    md += ["", "## Team-season ranks (30 teams)", "", "| metric | rank Spearman | max |rank shift| | median |rank shift| | teams whose rank changes |", "|---|---|---|---|---|"]
    md += [f"| {r['metric']} | {r['rank_spearman']:.3f} | {r['max_abs_rank_shift']} | {r['median_abs_rank_shift']:.1f} | {r['teams_with_rank_change']} |" for r in rows if r["level"] == "team_season"]
    md += ["", "## Context dependence (construct check, |naive − live| per possession)", "", "| metric | clean n | clean median | clean p90 | non-live n | non-live median | non-live p90 | MWU p (two-sided, descriptive) |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {m} | {c['clean_n']:,} | {c['clean_median_abs_change']:.3f} | {c['clean_p90']:.3f} | {c['nonlive_n']:,} | {c['nonlive_median_abs_change']:.3f} | {c['nonlive_p90']:.3f} | {c['mannwhitney_p_two_sided']:.2e} |" for m, c in ctx.items()]
    md += ["", "Clean = LIVE_CONTINUOUS_PLAY (by construction |Δ| ≈ 0 there: ≥ 95 % of frames are live); non-live = TIMEOUT / FREE_THROW / SUBSTITUTION_OR_ADMIN / OOB / MADE_BASKET classes. Median |Δ| by non-live class: " + "; ".join(f"{m}: " + ", ".join(f"{k} {v:.2f}" for k, v in c["nonlive_class_breakdown_median"].items()) for m, c in ctx.items()), "",
           "## timeout windows — structure only", "",
           f"Windows with ≥ 1 member possession in the universe: {case['windows_with_members_in_universe']:,}; with ≥ 1 non-live-class member: **{case['frac_windows_any_nonlive']:.3f}**; member possessions in a non-live class: {case['frac_members_nonlive_class']:.3f}; member interval frames that are non-live: **{case['frac_member_interval_frames_nonlive']:.3f}**; of the frames the frozen chain actually consumed (closed row-span mask), stopped-clock share: **{case['frac_member_row_span_frames_stopped_clock']:.3f}**. No TSS or effect quantity is computed here."]
    (R / "audit" / "DISTORTION.md").write_text("\n".join(md) + "\n")
    print(D[["level", "metric", "n_pairs", "paired_mean_diff_naive_minus_live", "standardized_diff", "pearson", "spearman", "mae", "p90_abs_change"]].round(3).to_string()); print(json.dumps(case, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
