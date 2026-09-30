#!/usr/bin/env python3
"""FRESH-CLONE REPRODUCIBILITY: 25-game deterministic subset, end-to-end from repository code + public-mirror inputs.

Games: the 25 smallest sha256(game_id) among the game ids of the shared alignment table (deterministic).
Pipeline (all producers imported from the clone itself): raw ingest + dedup + shot calibration + held-out turnover validation
(src/clock_latency_calibration.run_game) → aggregation/quality flags (src/aggregate_clock_latency.row_from)
→ curve taxonomy (curve-taxonomy rule) → structural consequence table (shot / turnover wrong-team rates at 0 s, +4 s,
per-game lead; global_shift.game_events). Compares to the main-artifact values. Screen-based consequences need withheld
event tables → INPUT_ACCESS_MANUAL (not attempted here).
Usage: python3 fresh_clone_subset.py --json-dir <raw sportvu json dir> --pbp <PlayByPlayV3 parquet> --out <dir> [--reference <main repo root>]
"""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve(); ROOT = HERE.parents[1]   # repo root of THIS clone
sys.path.insert(0, str(HERE.parent))
import clock_latency_calibration as CLC  # noqa: E402
import aggregate_clock_latency as AGG  # noqa: E402
import global_shift as GS  # noqa: E402


def taxonomy(row: dict, curve: list) -> str:
    """configs/CURVE_TAXONOMY.yaml, applied to the aggregate row + curve."""
    if row["quality_status"] != "CALIBRATED":
        return "INSUFFICIENT"
    if row["drift_status"] == "MATERIALLY_DRIFTING":
        return "DRIFTING"
    if row["bimodal_curve"]:
        return "MULTIMODAL"
    r = np.array([c["rate"] for c in curve]); width = (r >= r.max() - 0.02).sum() * 0.5
    return "FLAT_PLATEAU" if width >= 2.5 else "SHARP_UNIMODAL"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--json-dir", required=True); ap.add_argument("--pbp", required=True); ap.add_argument("--out", required=True); ap.add_argument("--reference", default=None); ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args(); out = Path(a.out); (out / "games").mkdir(parents=True, exist_ok=True); t0 = time.time()
    shared = pd.read_csv(ROOT / "results" / "clock_alignment_v1.csv", dtype={"game_id": str})
    pick = sorted(shared.game_id, key=lambda g: hashlib.sha256(g.encode()).hexdigest())[: a.n]; sub = shared[shared.game_id.isin(pick)].set_index("game_id")
    pbp = pd.read_parquet(a.pbp); pbp["gameId"] = pbp.gameId.astype(str).str.zfill(10)
    rows, cons = [], []
    for gid in pick:
        stem = sub.loc[gid, "stem"]; jp = Path(a.json_dir) / f"{stem}.json"
        r = CLC.run_game(jp, pbp[pbp.gameId == gid], out, source_lead=None)                      # ingest, dedup, shot calibration, turnover holdout
        agg = AGG.row_from(json.load(open(out / "games" / f"{gid}.json"))); agg["taxonomy_class"] = taxonomy(agg, r["curve"]); rows.append(agg)
        GS.CACHE = out / "global_shift"; GS.CACHE.mkdir(exist_ok=True)
        ev = GS.game_events((gid, stem, float(agg["calibrated_lead_s"]), pbp[pbp.gameId == gid].to_dict("records")))
        cons.append({"game_id": gid, **{k: v for k, v in ev.items() if k not in ("to_curve",)}})
    A = pd.DataFrame(rows); C = pd.DataFrame(cons); A.to_csv(out / "alignment_subset.csv", index=False); C.to_csv(out / "consequence_subset.csv", index=False)
    summ = {"n_games": len(pick), "game_ids": pick, "runtime_s": round(time.time() - t0, 1), "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "clone_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(), "sha256_alignment_subset_csv": hashlib.sha256(open(out / "alignment_subset.csv", "rb").read()).hexdigest(),
            "pooled": {m: {"shot_wrong_team": float(1 - C[f"shot_agree_{m}"].sum() / C[f"shot_n_{m}"].sum()), "turnover_wrong_team": float(1 - C[f"to_agree_{m}"].sum() / C[f"to_n_{m}"].sum())} for m in ("M0", "M1", "M2")},
            "taxonomy_counts": A.taxonomy_class.value_counts().to_dict(), "lead_status_counts": A.lead_status.value_counts().to_dict()}
    if a.reference:
        ref = pd.read_csv(Path(a.reference) / "results" / "taxonomy_by_game.csv", dtype={"game_id": str}).set_index("game_id")
        m = A.set_index("game_id").join(ref[["calibrated_lead_s", "lead_status", "taxonomy_class", "shot_rate_calibrated", "to_rate_calibrated"]], rsuffix="_ref")
        summ["agreement_with_main"] = {"lead_identical": int((m.calibrated_lead_s == m.calibrated_lead_s_ref).sum()), "status_identical": int((m.lead_status == m.lead_status_ref).sum()), "taxonomy_identical": int((m.taxonomy_class == m.taxonomy_class_ref).sum()),
                                       "max_abs_shot_rate_diff": float((m.shot_rate_calibrated - m.shot_rate_calibrated_ref).abs().max()), "max_abs_to_rate_diff": float((m.to_rate_calibrated - m.to_rate_calibrated_ref).abs().max()), "n": int(len(m))}
        gsr = Path(a.reference) / "results" / "global_shift_by_game.csv"
        if gsr.exists():
            g = pd.read_csv(gsr, dtype={"game_id": str}).set_index("game_id"); mm = C.set_index("game_id").join(g[["to_agree_M1", "to_n_M1", "shot_agree_M1"]], rsuffix="_ref")
            summ["agreement_with_main"]["global_shift_M1_identical"] = int(((mm.to_agree_M1 == mm.to_agree_M1_ref) & (mm.to_n_M1 == mm.to_n_M1_ref) & (mm.shot_agree_M1 == mm.shot_agree_M1_ref)).sum())
    json.dump(summ, open(out / "fresh_clone_summary.json", "w"), indent=2); print(json.dumps(summ, indent=1)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
