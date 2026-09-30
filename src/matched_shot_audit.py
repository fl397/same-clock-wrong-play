#!/usr/bin/env python3
"""Matched-shot / common-sample check — rules specified in configs/matched_shot_audit.yaml before this
script produced any number. Reads the regenerated per-shot spacing cache only after the reproduction
check passes. Writes results/matched_shot_audit.{csv,json} and audit/MATCHED_SHOT_AUDIT.md.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

R = Path(__file__).resolve().parents[1]; CA = Path(os.environ.get("SPACING_TABLE_DIR", R / "results"))
KEY = ["game_id", "period", "secs", "shot_value", "made"]
REF_NAIVE_Q4Q1 = 0.0938


def efg(x: pd.DataFrame) -> float:
    return float((x.made.sum() + 0.5 * (x.made & (x.shot_value == 3)).sum()) / len(x))


def quartiles(g: pd.DataFrame, col: str) -> np.ndarray:
    qs = g[col].quantile([.25, .5, .75]).values
    return np.digitize(g[col], qs)


def main() -> int:
    committed = pd.read_csv(sys.argv[1]); regen = pd.read_csv(CA / "results" / "external_artifact_generalization.csv")
    m = committed.merge(regen, on=["axis", "quartile"], suffixes=("_c", "_r"))
    gate = {"n_equal": bool((m.n_c == m.n_r).all()), "max_abs_efg": float((m.efg_c - m.efg_r).abs().max()),
            "max_abs_hull": float((m.mean_hull_sqft_c - m.mean_hull_sqft_r).abs().max()), "max_abs_share3": float((m.share_3pt_c - m.share_3pt_r).abs().max())}
    gate["pass"] = gate["n_equal"] and max(gate["max_abs_efg"], gate["max_abs_hull"], gate["max_abs_share3"]) <= 1e-9
    print("[gate]", gate)
    if not gate["pass"]:
        (R / "results" / "matched_shot_audit.json").write_text(json.dumps({"reproduction_gate": gate, "status": "STOP_GATE_FAIL"}, indent=2)); return 1
    S = pd.read_parquet(CA / "data" / "spacing_at_shot_generalization.parquet")
    out = {"reproduction_gate": gate, "rules": "configs/matched_shot_audit.yaml",}
    nv, cl = S[S.axis == "naive"], S[S.axis == "calibrated"]
    out["original_naive_n"], out["original_corrected_n"] = int(len(nv)), int(len(cl))
    dup_n = nv.duplicated(KEY, keep=False); dup_c = cl.duplicated(KEY, keep=False)
    out["duplicate_keys"] = {"naive_rows_in_duplicated_keys": int(dup_n.sum()), "corrected_rows_in_duplicated_keys": int(dup_c.sum()), "treatment": "excluded from S_intersection"}
    nv1 = nv[~dup_n].set_index(KEY); cl1 = cl[~dup_c].set_index(KEY)
    common = nv1.index.intersection(cl1.index)
    I = pd.DataFrame({"hull_naive": nv1.loc[common, "hull_area"].values, "hull_corrected": cl1.loc[common, "hull_area"].values}, index=common).reset_index()
    out["intersection_n"] = int(len(I)); out["naive_only_n"] = int(len(nv1) - len(I)); out["corrected_only_n"] = int(len(cl1) - len(I))
    rows = []
    for axis, col in (("naive", "hull_naive"), ("corrected", "hull_corrected")):
        q = quartiles(I, col); tab = []
        for k in range(4):
            x = I[q == k]; tab.append({"sample": "S_intersection", "axis": axis, "quartile": f"Q{k+1}", "n": int(len(x)), "mean_hull_sqft": float(x[col].mean()), "efg": efg(x), "share_3pt": float((x.shot_value == 3).mean())})
        rows += tab; e = [t["efg"] for t in tab]
        out[f"common_{axis}"] = {"efg": e, "n": [t["n"] for t in tab], "q4_minus_q1": e[3] - e[0], "monotone_nondecreasing": bool(all(e[i] <= e[i + 1] for i in range(3))),
                                "spearman_rho_quartile_means": float(spearmanr([1, 2, 3, 4], e).correlation)}
    # secondary fixed-rank check: quartiles by naive ranks once; corrected-window hull summaries by the same groups
    qn = quartiles(I, "hull_naive"); fixed = []
    for k in range(4):
        x = I[qn == k]
        fixed.append({"sample": "S_intersection_fixed_naive_rank", "axis": "naive_groups", "quartile": f"Q{k+1}", "n": int(len(x)), "mean_hull_sqft": float(x.hull_naive.mean()), "efg": efg(x),
                      "share_3pt": float((x.shot_value == 3).mean()), "corrected_hull_mean": float(x.hull_corrected.mean()), "corrected_hull_median": float(x.hull_corrected.median())})
    out["fixed_rank_check"] = fixed; out["corr_hull_naive_vs_corrected_same_shots"] = float(I.hull_naive.corr(I.hull_corrected))
    rows += fixed
    # frozen decision rule
    nq = out["common_naive"]["q4_minus_q1"]; cq = out["common_corrected"]["q4_minus_q1"]
    if nq < REF_NAIVE_Q4Q1 / 3:
        cls = "SAMPLE_COMPOSITION_DOMINATES"
    elif nq >= 2 * REF_NAIVE_Q4Q1 / 3 and out["common_naive"]["monotone_nondecreasing"] and (cq <= nq / 3 or cq < 0):
        cls = "MATCHED_SAMPLE_CONFIRMS_ARTIFACT"
    else:
        cls = "MIXED_MEASUREMENT_AND_SELECTION"
    out["classification"] = cls
    out["abstract_sentence_valid"] = cls == "MATCHED_SAMPLE_CONFIRMS_ARTIFACT"; out["figure1_headline_valid"] = cls == "MATCHED_SAMPLE_CONFIRMS_ARTIFACT"
    out["required_edit"] = ("none" if cls == "MATCHED_SAMPLE_CONFIRMS_ARTIFACT" else
                            "Naive clock joining alters both analytical eligibility and the apparent spacing–efficiency relationship." if cls == "MIXED_MEASUREMENT_AND_SELECTION" else "the Figure 1 headline would not be supported")
    pd.DataFrame(rows).to_csv(R / "results" / "matched_shot_audit.csv", index=False)
    (R / "results" / "matched_shot_audit.json").write_text(json.dumps(out, indent=2))
    cn, cc = out["common_naive"], out["common_corrected"]
    md = ["# Matched-shot / common-sample validation of the spacing–eFG comparison", "",
          f"Rules frozen before the results were computed (`docs/validation/MATCHED_SHOT_VALIDATION.md`, `configs/matched_shot_audit.yaml`). Producer `src/matched_shot_audit.py`; inputs = the per-shot spacing table regenerated by the unchanged `src/external_artifact_generalization.py`. Reproduction gate: n equal = {gate['n_equal']}, max |Δ eFG| = {gate['max_abs_efg']:.2e}, max |Δ hull| = {gate['max_abs_hull']:.2e}, max |Δ 3PA share| = {gate['max_abs_share3']:.2e} → **{'PASS' if gate['pass'] else 'FAIL'}**.", "",
          "## Samples", "", f"| original naive N | original corrected N | intersection N | naive-only N | corrected-only N | duplicated-key rows excluded (naive / corrected) |", "|---|---|---|---|---|---|",
          f"| {out['original_naive_n']:,} | {out['original_corrected_n']:,} | **{out['intersection_n']:,}** | {out['naive_only_n']:,} | {out['corrected_only_n']:,} | {out['duplicate_keys']['naive_rows_in_duplicated_keys']} / {out['duplicate_keys']['corrected_rows_in_duplicated_keys']} |", "",
          "## Common sample — quartiles per axis (boundaries from S_intersection)", "",
          "| axis | Q1 n / eFG | Q2 n / eFG | Q3 n / eFG | Q4 n / eFG | Q4 − Q1 | monotone | Spearman ρ |", "|---|---|---|---|---|---|---|---|"]
    for axis, c in (("naive", cn), ("corrected", cc)):
        md.append(f"| {axis} | " + " | ".join(f"{n:,} / {e:.4f}" for n, e in zip(c['n'], c['efg'])) + f" | **{c['q4_minus_q1']:+.4f}** | {c['monotone_nondecreasing']} | {c['spearman_rho_quartile_means']:+.2f} |")
    md += ["", f"Reference: original naive Q4 − Q1 = +0.0938 (27,563 shots); original corrected Q4 − Q1 = −0.0188 (64,764 shots).", "",
           "## Secondary fixed-rank check (diagnostic only; quartiles assigned once by naive ranks)", "", "| naive-rank group | n | naive eFG | naive hull mean | corrected hull mean | corrected hull median |", "|---|---|---|---|---|---|"]
    md += [f"| {f['quartile']} | {f['n']:,} | {f['efg']:.4f} | {f['mean_hull_sqft']:.0f} | {f['corrected_hull_mean']:.0f} | {f['corrected_hull_median']:.0f} |" for f in fixed]
    md += ["", f"Correlation of naive-window and corrected-window hull area on the same shots: {out['corr_hull_naive_vs_corrected_same_shots']:.3f}.", "",
           f"## Classification (frozen rule): **{cls}**", "",
           f"- Current abstract sentence valid? **{'YES' if out['abstract_sentence_valid'] else 'NO'}**", f"- Current Figure 1 headline valid? **{'YES' if out['figure1_headline_valid'] else 'NO'}**",
           f"- Required edit: {out['required_edit']}"]
    (R / "audit" / "MATCHED_SHOT_AUDIT.md").write_text("\n".join(md) + "\n"); print(json.dumps({k: v for k, v in out.items() if k not in ('fixed_rank_check',)}, indent=1)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
