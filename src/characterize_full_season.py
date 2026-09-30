#!/usr/bin/env python3
"""+ full-season characterization of the PBP→tracking lead and the frozen curve taxonomy.
Reads ONLY results/clock_alignment_v1.csv (+ manifest) and configs/CURVE_TAXONOMY.yaml. Writes
results/full_season_table.csv, results/taxonomy_by_game.csv, results/taxonomy_summary.csv, results/strata_descriptive.csv,
audit/FULL_SEASON_CHARACTERIZATION.md, audit/CURVE_TAXONOMY_RESULTS.md. Strata are DESCRIPTIVE_ONLY.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd, yaml

R = Path(__file__).resolve().parents[1]; SH = R / "results"
T = pd.read_csv(SH / "clock_alignment_v1.csv", dtype={"game_id": str})
man = json.load(open(SH / "clock_alignment_v1_manifest.json")); cfg = yaml.safe_load((R / "configs" / "CURVE_TAXONOMY.yaml").read_text())


def classify(r):
    if r.quality_status != "CALIBRATED":
        return "INSUFFICIENT"
    if r.drift_status == "MATERIALLY_DRIFTING":
        return "DRIFTING"
    if bool(r.bimodal_curve):
        return "MULTIMODAL"
    if r.plateau_width_s_within_0p02 >= 2.5:
        return "FLAT_PLATEAU"
    return "SHARP_UNIMODAL"


def q(x, p):
    return float(np.nanpercentile(x, p))


def main() -> int:
    T["taxonomy_class"] = T.apply(classify, axis=1)
    dstr = T.stem.str.extract(r"(\d{2}\.\d{2}\.\d{4})")[0]; T["month"] = dstr.str.slice(0, 2); T["date"] = pd.to_datetime(dstr, format="%m.%d.%Y", errors="coerce")
    T["home_team"] = T.stem.str.extract(r"\.at\.([A-Z]{3})")[0]; T["away_team"] = T.stem.str.extract(r"\.([A-Z]{3})\.at\.")[0]
    T["argmax_minus_edge_s"] = T.calibrated_lead_s - T.rising_edge_lead_s
    T.to_csv(R / "results" / "taxonomy_by_game.csv", index=False)
    V = T[T.lead_status == "CLOCK_CALIBRATION_VALIDATED"]; C = T[T.quality_status == "CALIBRATED"]
    # counts
    counts = {"raw_files": int(len(T)), "parseable": int(len(T)), "with_tracking_moments": int((T.quality_status != "NO_TRACKING_MOMENTS").sum()),
              "calibratable (>=20 labelled shots, >=5 turnovers)": int(len(C)), "validated": int(len(V)), "ambiguous (MULTIMODAL within one event)": int((T.lead_status == "AMBIGUOUS_LEAD").sum()),
              "drifting (|dH|>2 s)": int((T.lead_status == "DRIFTING_LEAD").sum()), "held-out failures (TO agreement < 0.80)": int((T.lead_status == "HOLDOUT_FAIL").sum())}
    lead = V.calibrated_lead_s
    dist = {"n": int(len(V)), "median": float(lead.median()), "mean": float(lead.mean()), "sd": float(lead.std()), "IQR": [q(lead, 25), q(lead, 75)], "p05": q(lead, 5), "p95": q(lead, 95), "range": [float(lead.min()), float(lead.max())],
            "shot_rate_naive_pooled": float((V.shot_rate_naive * V.shot_n_naive).sum() / V.shot_n_naive.sum()), "shot_rate_calibrated_pooled": float(V.shot_agree_calibrated.sum() / V.shot_n_calibrated.sum()),
            "to_rate_naive_pooled": float((V.to_rate_naive * V.to_n_naive).sum() / V.to_n_naive.sum()), "to_rate_calibrated_pooled": float(V.to_agree_calibrated.sum() / V.to_n_calibrated.sum()),
            "per_game_shot_rate_naive_median": float(V.shot_rate_naive.median()), "per_game_shot_rate_calibrated_median": float(V.shot_rate_calibrated.median()), "per_game_shot_rate_calibrated_min": float(V.shot_rate_calibrated.min()),
            "per_game_to_rate_naive_median": float(V.to_rate_naive.median()), "per_game_to_rate_calibrated_median": float(V.to_rate_calibrated.median()), "per_game_to_rate_calibrated_min": float(V.to_rate_calibrated.min()),
            "calibration_shots_per_game_median": float(V.shot_n_calibrated.median()), "calibration_shots_total": int(V.shot_n_calibrated.sum()), "turnovers_per_game_median": float(V.to_n_calibrated.median()), "turnovers_total": int(V.to_n_calibrated.sum()),
            "all_calibrated_games": {"n": int(len(C)), "median": float(C.calibrated_lead_s.median()), "IQR": [q(C.calibrated_lead_s, 25), q(C.calibrated_lead_s, 75)], "shot_calibrated_pooled": float(C.shot_agree_calibrated.sum() / C.shot_n_calibrated.sum()), "to_calibrated_pooled": float(C.to_agree_calibrated.sum() / C.to_n_calibrated.sum())}}
    pd.DataFrame([{"quantity": k, "value": v} for k, v in {**counts, **{f"validated_{k}": v for k, v in dist.items() if k != "all_calibrated_games"}}.items()]).to_csv(R / "results" / "full_season_table.csv", index=False)
    # strata (descriptive only)
    rows = []
    for name, col in (("month", "month"), ("home_team", "home_team")):
        for k, g in V.groupby(col):
            rows.append({"stratum": name, "level": k, "n_validated": len(g), "lead_median": g.calibrated_lead_s.median(), "lead_mean": g.calibrated_lead_s.mean(), "lead_IQR_low": q(g.calibrated_lead_s, 25), "lead_IQR_high": q(g.calibrated_lead_s, 75), "n_all_games": int((T[col] == k).sum()), "validated_share": len(g) / max(int((T[col] == k).sum()), 1)})
    H = C.dropna(subset=["lead_H1", "lead_H2"])
    rows.append({"stratum": "half", "level": "H1", "n_validated": len(H), "lead_median": H.lead_H1.median(), "lead_mean": H.lead_H1.mean(), "lead_IQR_low": q(H.lead_H1, 25), "lead_IQR_high": q(H.lead_H1, 75)})
    rows.append({"stratum": "half", "level": "H2", "n_validated": len(H), "lead_median": H.lead_H2.median(), "lead_mean": H.lead_H2.mean(), "lead_IQR_low": q(H.lead_H2, 25), "lead_IQR_high": q(H.lead_H2, 75)})
    rows.append({"stratum": "half", "level": "H2-H1 signed", "n_validated": len(H), "lead_median": (H.lead_H2 - H.lead_H1).median(), "lead_mean": (H.lead_H2 - H.lead_H1).mean(), "lead_IQR_low": q(H.lead_H2 - H.lead_H1, 25), "lead_IQR_high": q(H.lead_H2 - H.lead_H1, 75)})
    S = pd.DataFrame(rows); S.to_csv(R / "results" / "strata_descriptive.csv", index=False)
    # taxonomy summary
    tx = []
    for cls, g in T.groupby("taxonomy_class"):
        cal = g[g.quality_status == "CALIBRATED"]
        tx.append({"class": cls, "n": len(g), "fraction": len(g) / len(T), "plateau_width_median": g.plateau_width_s_within_0p02.median(), "plateau_width_IQR_low": q(g.plateau_width_s_within_0p02, 25), "plateau_width_IQR_high": q(g.plateau_width_s_within_0p02, 75),
                   "abs_half_diff_median": g.abs_half_lead_diff_s.median(), "abs_half_diff_IQR_high": q(g.abs_half_lead_diff_s, 75), "argmax_minus_edge_median": g.argmax_minus_edge_s.median(),
                   "lead_median": g.calibrated_lead_s.median(), "to_rate_calibrated_pooled": (cal.to_agree_calibrated.sum() / cal.to_n_calibrated.sum()) if len(cal) else np.nan,
                   "to_rate_naive_pooled": ((cal.to_rate_naive * cal.to_n_naive).sum() / cal.to_n_naive.sum()) if len(cal) else np.nan, "shot_rate_calibrated_pooled": (cal.shot_agree_calibrated.sum() / cal.shot_n_calibrated.sum()) if len(cal) else np.nan,
                   "holdout_fail_n": int((g.holdout_status == "HOLDOUT_FAIL").sum()), "validated_n": int((g.lead_status == "CLOCK_CALIBRATION_VALIDATED").sum())})
    TX = pd.DataFrame(tx).set_index("class").loc[[c for c in ["SHARP_UNIMODAL", "FLAT_PLATEAU", "MULTIMODAL", "DRIFTING", "INSUFFICIENT"] if c in set(T.taxonomy_class)]].reset_index(); TX.to_csv(R / "results" / "taxonomy_summary.csv", index=False)
    # markdown
    md = ["# Full-season characterization (632 local SportVU games, 2015-16)", "", f"Source: `results/clock_alignment_v1.csv` (sha256 {man['sha256'][:16]}…), source-exact method (ismayc/tracking-study d21f8e3c, reproduction PASS). Leads are per game; calibration labels = shot-team agreement; held-out = turnover-team agreement.", "",
          "## Game accounting", "", "| stage | games |", "|---|---|"] + [f"| {k} | {v} |" for k, v in counts.items()] + [
          "", "## Lead distribution — CLOCK_CALIBRATION_VALIDATED games", "", "| quantity | value |", "|---|---|",
          f"| n | {dist['n']} |", f"| median / mean / sd (s) | {dist['median']:.2f} / {dist['mean']:.2f} / {dist['sd']:.2f} |", f"| IQR (s) | {dist['IQR'][0]:.1f} – {dist['IQR'][1]:.1f} |", f"| p05 / p95 (s) | {dist['p05']:.1f} / {dist['p95']:.1f} |", f"| range (s) | {dist['range'][0]:.1f} – {dist['range'][1]:.1f} |",
          f"| shot-team agreement, pooled, naive → calibrated | {dist['shot_rate_naive_pooled']:.3f} → {dist['shot_rate_calibrated_pooled']:.3f} ({dist['calibration_shots_total']:,} calibration shots; median {dist['calibration_shots_per_game_median']:.0f}/game) |",
          f"| per-game shot agreement, median naive → calibrated (min calibrated) | {dist['per_game_shot_rate_naive_median']:.3f} → {dist['per_game_shot_rate_calibrated_median']:.3f} ({dist['per_game_shot_rate_calibrated_min']:.3f}) |",
          f"| held-out turnover agreement, pooled, naive → calibrated | {dist['to_rate_naive_pooled']:.3f} → {dist['to_rate_calibrated_pooled']:.3f} ({dist['turnovers_total']:,} turnovers; median {dist['turnovers_per_game_median']:.0f}/game) |",
          f"| per-game turnover agreement, median naive → calibrated (min calibrated) | {dist['per_game_to_rate_naive_median']:.3f} → {dist['per_game_to_rate_calibrated_median']:.3f} ({dist['per_game_to_rate_calibrated_min']:.3f}) |",
          f"| all 631 calibrated games (any status): median lead / IQR / shots / turnovers | {dist['all_calibrated_games']['median']:.1f} s / {dist['all_calibrated_games']['IQR'][0]:.1f}–{dist['all_calibrated_games']['IQR'][1]:.1f} / {dist['all_calibrated_games']['shot_calibrated_pooled']:.3f} / {dist['all_calibrated_games']['to_calibrated_pooled']:.3f} |",
          "", "Lead histogram (validated): " + ", ".join(f"{k:.1f}s: {n}" for k, n in lead.value_counts().sort_index().items()), "",
          "## Strata — DESCRIPTIVE_ONLY (no subgroup inference)", "", "| stratum | level | n validated | lead median | mean | IQR |", "|---|---|---|---|---|---|"] + [f"| {r.stratum} | {r.level} | {int(r.n_validated)} | {r.lead_median:.2f} | {r.lead_mean:.2f} | {r.lead_IQR_low:.1f}–{r.lead_IQR_high:.1f} |" for r in S[S.stratum != "home_team"].itertuples()] + [
          "", f"Home-team stratum (30 levels; per-game lead attributed to the home arena's scorer's table) is in `results/strata_descriptive.csv`: lead medians range {S[S.stratum=='home_team'].lead_median.min():.1f}–{S[S.stratum=='home_team'].lead_median.max():.1f} s across arenas (n per arena {int(S[S.stratum=='home_team'].n_validated.min())}–{int(S[S.stratum=='home_team'].n_validated.max())}). Home/away as a *game* property is not applicable to a per-game quantity.",
          "File provenance: all 632 files are the linouk23 2015-16 mirror (one file with 466 event containers and zero moments: 0021500659).", "",
          "First vs second half: per-half leads exist for the 631 calibrated games; H1 median {:.1f} s, H2 median {:.1f} s; signed H2−H1 median {:.1f} s, IQR {:.1f}–{:.1f} s.".format(H.lead_H1.median(), H.lead_H2.median(), (H.lead_H2 - H.lead_H1).median(), q(H.lead_H2 - H.lead_H1, 25), q(H.lead_H2 - H.lead_H1, 75))]
    (R / "audit" / "FULL_SEASON_CHARACTERIZATION.md").write_text("\n".join(md) + "\n")
    md2 = ["# Calibration-uncertainty taxonomy (frozen rules: configs/CURVE_TAXONOMY.yaml)", "", "| class | n | fraction | plateau width median (IQR) s | abs half-diff median (p75) s | argmax − rising edge median s | lead median | shots calibrated | TO naive → calibrated | holdout-fail n | validated n |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in TX.itertuples():
        md2.append(f"| {r._1 if hasattr(r,'_1') else r.Index} | {r.n} | {r.fraction:.3f} | {r.plateau_width_median:.1f} ({r.plateau_width_IQR_low:.1f}–{r.plateau_width_IQR_high:.1f}) | {r.abs_half_diff_median:.1f} ({r.abs_half_diff_IQR_high:.1f}) | {r.argmax_minus_edge_median:.1f} | {r.lead_median:.1f} | {r.shot_rate_calibrated_pooled:.3f} | {r.to_rate_naive_pooled:.3f} → {r.to_rate_calibrated_pooled:.3f} | {r.holdout_fail_n} | {r.validated_n} |")
    md2 += ["", f"Argmax − rising-edge over all calibrated games: median {C.argmax_minus_edge_s.median():.1f} s, IQR {q(C.argmax_minus_edge_s,25):.1f}–{q(C.argmax_minus_edge_s,75):.1f} s; distribution: " + ", ".join(f"{k:.1f}s: {n}" for k, n in C.argmax_minus_edge_s.value_counts().sort_index().items()),
           "", "Reading: the source-exact argmax is retained. On FLAT_PLATEAU curves the lead is only identified to within the plateau width; the held-out turnover agreement stays high in every shape class (the 2-s label window is tolerant), so plateau width is an *identification* limitation for boundary shifting, not a labelling failure. HOLDOUT_FAIL is reported per class as a validation outcome."]
    (R / "audit" / "CURVE_TAXONOMY_RESULTS.md").write_text("\n".join(md2) + "\n")
    print(json.dumps({"counts": counts, "dist": {k: v for k, v in dist.items() if k != "all_calibrated_games"}}, indent=1)); print(TX.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
