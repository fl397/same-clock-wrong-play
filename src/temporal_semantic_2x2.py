#!/usr/bin/env python3
"""TEMPORAL × SEMANTIC 2×2 (rules frozen in configs/temporal_semantic_2x2.yaml).

Cells: A naive(0 s)+raw, B naive+live, C calibrated+raw, D calibrated+live. Same possession set (301-game live-play universe,
possession intervals). M1/M2/M3 = the live-play project's frozen definitions (imported unchanged from
src/build_segments.py); M4 = held-out turnover-window team agreement using only the cell's frames
(source nearest-player labeler from src/clock_latency_calibration.py, unchanged). Per-game cache data/2x2/.
"""
from __future__ import annotations
import argparse, json, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_segments import load_frames, live_flags, frame_metrics, MIN_FRAMES  # noqa: E402  (frozen live-play definitions)
from clock_latency_calibration import frames_from_events, possession_frames, Labeler, load_pbp, agreement  # noqa: E402
SHARED = R / "results" / "clock_alignment_v1.csv"
JSON_DIR = Path(os.environ.get("SPORTVU_JSON_DIR", "data/external/sportvu/json")); V3 = os.environ.get("V3_POSSESSIONS_PARQUET", "data/derived/possessions_v3.parquet"); PBP = Path(os.environ.get("PBP_PARQUET", "data/external/pbp/2015-16/all.parquet"))
CACHE = R / "data" / "2x2"; CELLS = {"A": (0.0, False), "B": (0.0, True), "C": (None, False), "D": (None, True)}


def game_cells(args) -> dict:
    gid, stem, lead, pbp_rows, v3_rows = args
    out = CACHE / f"{gid}.json"
    if out.exists():
        return json.load(open(out))
    g = json.load(open(JSON_DIR / f"{stem}.json"))
    # live-play frame table (utc dedup) + live flags
    recs, ents = [], []
    for ev in g.get("events") or []:
        for m in ev.get("moments") or []:
            if m[0] is None or m[1] is None or m[2] is None:
                continue
            recs.append((int(m[0]), int(m[1]), float(m[2]), np.nan if m[3] is None else float(m[3]), len(m[5]))); ents.append(m[5])
    f = pd.DataFrame(recs, columns=["period", "utc", "clock", "shot_clock", "n_ent"]); f["ent_idx"] = np.arange(len(f))
    f = f.drop_duplicates(["period", "utc"], keep="first").sort_values(["period", "utc"]).reset_index(drop=True); f = live_flags(f)
    live_clocks = {int(p): set(x.clock[x.live].round(2)) for p, x in f.groupby("period")}
    # latency-engine frames (period, clock, player dedup) for M4
    fr, _ = frames_from_events(g["events"]); poss_all = possession_frames(fr)
    poss_live = poss_all[[round(c, 2) in live_clocks.get(int(p), set()) for p, c in zip(poss_all.period, poss_all.game_clock)]]
    lab_raw, lab_live = Labeler(poss_all), Labeler(poss_live)
    p = load_pbp(pd.DataFrame(pbp_rows)); tos = p[p.is_turnover & (p.team_id != 0)]; shots = p[p.is_fga & (p.team_id != 0)]
    m4 = {}
    for cell, (L, live) in CELLS.items():
        L_ = lead if L is None else L; lab = lab_live if live else lab_raw
        a, n = agreement(lab, tos, L_); a2, n2 = agreement(lab, shots, L_); m4[cell] = {"to_agree": a, "to_n": n, "shot_agree": a2, "shot_n": n2}
    # possession intervals and M1-M3 per cell
    v3 = pd.DataFrame(v3_rows); rows = []
    for period, gp in v3.sort_values(["period", "end_actionNumber"]).groupby("period"):
        fp = f[f.period == period].reset_index(drop=True); clk = fp.clock.values; live = fp.live.values
        prev_end = 720.0 if period <= 4 else 300.0
        for r in gp.to_dict("records"):
            e = float(r["end_clock_seconds"]); off = int(r["offense_team_id"]); rec = {"game_id": gid, "possession_id": r["possession_id"], "period": int(period), "interval_s": prev_end - e}
            if prev_end - e > 0:
                for cell, (L, lv) in CELLS.items():
                    L_ = lead if L is None else L; m = (clk > e + L_) & (clk <= prev_end + L_)
                    idx = np.where(m & live)[0] if lv else np.where(m)[0]
                    mm = frame_metrics(idx, fp, ents, off) if len(idx) >= MIN_FRAMES else {"n_usable": 0, "M1": np.nan, "M2": np.nan, "M3": np.nan}
                    rec[f"n_{cell}"] = int(len(idx)); rec[f"M1_{cell}"], rec[f"M2_{cell}"], rec[f"M3_{cell}"] = mm["M1"], mm["M2"], mm["M3"]
            rows.append(rec); prev_end = e
    res = {"game_id": gid, "lead": lead, "m4": m4, "possessions": rows}
    json.dump(res, open(out, "w")); return res


def stage_build(workers: int) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    T = pd.read_csv(SHARED, dtype={"game_id": str}); v3 = pd.read_parquet(V3); v3["game_id"] = v3.game_id.astype(str)
    U = T[(T.lead_status == "CLOCK_CALIBRATION_VALIDATED") & T.game_id.isin(set(v3.game_id)) & T.stem.map(lambda s: (JSON_DIR / f"{s}.json").exists())]
    pbp = pd.read_parquet(PBP); pbp["gameId"] = pbp.gameId.astype(str).str.zfill(10)
    jobs = [(r.game_id, r.stem, float(r.calibrated_lead_s), pbp[pbp.gameId == r.game_id].to_dict("records"), v3[v3.game_id == r.game_id].to_dict("records")) for r in U.itertuples() if not (CACHE / f"{r.game_id}.json").exists()]
    print(f"[2x2] universe {len(U)} games; to do {len(jobs)}", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, fu in enumerate(as_completed([ex.submit(game_cells, j) for j in jobs])):
            fu.result()
            if (i + 1) % 25 == 0:
                print(f"[2x2] {i + 1}/{len(jobs)}", flush=True)
    return 0


def stage_report() -> int:
    recs = [json.load(open(f)) for f in sorted(CACHE.glob("*.json"))]
    P = pd.DataFrame([r for x in recs for r in x["possessions"]]); P = P[P.interval_s > 0]
    P.to_parquet(R / "data" / "temporal_semantic_2x2_possessions.parquet", index=False)
    out = {"n_games": len(recs), "n_possessions_universe": int(len(P))}
    m4 = {c: {"to_agree": sum(x["m4"][c]["to_agree"] for x in recs), "to_n": sum(x["m4"][c]["to_n"] for x in recs), "shot_agree": sum(x["m4"][c]["shot_agree"] for x in recs), "shot_n": sum(x["m4"][c]["shot_n"] for x in recs)} for c in CELLS}
    for c in m4:
        m4[c]["turnover_agreement"] = m4[c]["to_agree"] / max(m4[c]["to_n"], 1); m4[c]["shot_agreement"] = m4[c]["shot_agree"] / max(m4[c]["shot_n"], 1)
    out["M4"] = m4; met = {}
    for M in ("M1", "M2", "M3"):
        cols = [f"{M}_{c}" for c in CELLS]; both = P.dropna(subset=cols); d = {"n_paired_all_cells": int(len(both)), "n_valid_per_cell": {c: int(P[f"{M}_{c}"].notna().sum()) for c in CELLS}}
        for c in CELLS:
            d[f"mean_{c}"] = float(both[f"{M}_{c}"].mean()); d[f"sd_{c}"] = float(both[f"{M}_{c}"].std())
        sdD = both[f"{M}_D"].std()
        for pair in (("A", "B"), ("A", "C"), ("A", "D"), ("B", "D"), ("C", "D")):
            diff = both[f"{M}_{pair[0]}"] - both[f"{M}_{pair[1]}"]
            d[f"paired_{pair[0]}_minus_{pair[1]}"] = float(diff.mean()); d[f"std_diff_{pair[0]}_minus_{pair[1]}_over_sdD"] = float(diff.mean() / sdD); d[f"mae_{pair[0]}_{pair[1]}"] = float(diff.abs().mean()); d[f"p90_abs_{pair[0]}_{pair[1]}"] = float(diff.abs().quantile(.9))
            d[f"spearman_{pair[0]}_{pair[1]}"] = float(spearmanr(both[f"{M}_{pair[0]}"], both[f"{M}_{pair[1]}"])[0])
        d["decomposition"] = {"temporal_A_to_C": d["paired_A_minus_C"], "semantic_A_to_B": d["paired_A_minus_B"], "combined_A_to_D": d["paired_A_minus_D"], "interaction": d["paired_A_minus_D"] - (d["paired_A_minus_C"] + d["paired_A_minus_B"]),
                              "mae_temporal_A_C": d["mae_A_C"], "mae_semantic_A_B": d["mae_A_B"], "mae_combined_A_D": d["mae_A_D"]}
        met[M] = d
    out["metrics"] = met; json.dump(out, open(R / "results" / "temporal_semantic_2x2.json", "w"), indent=2)
    md = ["# TEMPORAL × SEMANTIC 2×2 (rules frozen before the results; producer src/temporal_semantic_2x2.py)", "",
          f"Universe: {out['n_games']} validated games, {out['n_possessions_universe']:,} possession intervals (same set in all cells; paired statistics on intervals with a value in all four cells).", "",
          "## M4 — event/window team-assignment agreement (held-out turnovers; shots secondary)", "", "| cell | clock | frames | turnover agreement | n | shot agreement | n |", "|---|---|---|---|---|---|---|"]
    for c, (L, lv) in CELLS.items():
        md.append(f"| {c} | {'naive 0 s' if L == 0.0 else 'calibrated'} | {'live-only' if lv else 'raw'} | **{m4[c]['turnover_agreement']:.3f}** | {m4[c]['to_n']:,} | {m4[c]['shot_agreement']:.3f} | {m4[c]['shot_n']:,} |")
    md += ["", "## M1–M3 (paired on intervals valid in all cells)", ""]
    for M, unit in (("M1", "ft/s"), ("M2", "sq ft"), ("M3", "ft")):
        d = met[M]; md += [f"### {M} ({unit}) — paired n = {d['n_paired_all_cells']:,}; valid per cell A/B/C/D = {d['n_valid_per_cell']['A']:,}/{d['n_valid_per_cell']['B']:,}/{d['n_valid_per_cell']['C']:,}/{d['n_valid_per_cell']['D']:,}", "",
                         "| cell | mean | SD |", "|---|---|---|"] + [f"| {c} | {d[f'mean_{c}']:.3f} | {d[f'sd_{c}']:.3f} |" for c in CELLS] + ["",
                         "| contrast | paired mean diff | standardized (÷ SD_D) | MAE | p90 abs | Spearman |", "|---|---|---|---|---|---|"] + [
                         f"| {a}−{b} ({lab}) | {d[f'paired_{a}_minus_{b}']:+.3f} | {d[f'std_diff_{a}_minus_{b}_over_sdD']:+.3f} | {d[f'mae_{a}_{b}']:.3f} | {d[f'p90_abs_{a}_{b}']:.3f} | {d[f'spearman_{a}_{b}']:.3f} |" for a, b, lab in (("A", "B", "semantic"), ("A", "C", "temporal"), ("A", "D", "combined"), ("B", "D", "temporal given live"), ("C", "D", "semantic given calibrated"))] + [
                         "", f"Decomposition: temporal A→C {d['decomposition']['temporal_A_to_C']:+.3f}, semantic A→B {d['decomposition']['semantic_A_to_B']:+.3f}, combined A→D {d['decomposition']['combined_A_to_D']:+.3f}, interaction {d['decomposition']['interaction']:+.3f} (mean diffs); MAE temporal {d['decomposition']['mae_temporal_A_C']:.3f}, semantic {d['decomposition']['mae_semantic_A_B']:.3f}, combined {d['decomposition']['mae_combined_A_D']:.3f}.", ""]
    (R / "audit" / "TEMPORAL_SEMANTIC_2X2.md").write_text("\n".join(md) + "\n"); print(json.dumps({"M4": m4, "decomp": {M: met[M]["decomposition"] for M in met}, "spearman_AD": {M: met[M]["spearman_A_D"] for M in met}}, indent=1)); return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=["build", "report"], required=True); ap.add_argument("--workers", type=int, default=20); a = ap.parse_args()
    raise SystemExit(stage_build(a.workers) if a.stage == "build" else stage_report())
