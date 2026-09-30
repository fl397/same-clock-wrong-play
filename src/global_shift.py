#!/usr/bin/env python3
"""GLOBAL +4 s vs PER-GAME calibration (rules frozen in configs/global_shift_baseline.yaml).

Stage 'events' : per calibratable game, held-out turnover and shot agreement at leads 0.0 / 4.0 / per-game, plus the turnover
                 agreement curve over the 17-point lead grid (cache data/global_shift/<game_id>.json). Labeler unchanged
                 (src/clock_latency_calibration.py). Parallel.
Stage 'screens': existing detected on-ball screens on validated games: apparent onset < 0.5 s and possession reassignment at each method's lead.
Stage 'report' : results/global_shift_*.csv/json + audit/GLOBAL_SHIFT_BASELINE.md.
"""
from __future__ import annotations
import argparse, json, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PROJECT_ROOT", "."))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clock_latency_calibration import load_game_json, frames_from_events, possession_frames, Labeler, load_pbp, agreement, LEAD_GRID  # noqa: E402
SHARED = R / "results" / "clock_alignment_v1.csv"; TAX = R / "results" / "taxonomy_by_game.csv"
RAW = Path(os.environ.get("SPORTVU_JSON_DIR", "data/external/sportvu/json")); PBP = Path(os.environ.get("PBP_PARQUET", "data/external/pbp/2015-16/all.parquet"))
CACHE = R / "data" / "global_shift"; GLOBAL = 4.0
CLASSES = ["SHARP_UNIMODAL", "FLAT_PLATEAU", "MULTIMODAL", "DRIFTING"]


def game_events(args) -> dict:
    gid, stem, lead, pbp_rows = args
    out = CACHE / f"{gid}.json"
    if out.exists():
        return json.load(open(out))
    _, events, _ = load_game_json(RAW / f"{stem}.json"); fr, _ = frames_from_events(events); lab = Labeler(possession_frames(fr))
    p = load_pbp(pd.DataFrame(pbp_rows)); shots = p[p.is_fga & (p.team_id != 0)]; tos = p[p.is_turnover & (p.team_id != 0)]
    rec = {"game_id": gid, "lead": lead}
    for name, L in (("M0", 0.0), ("M1", GLOBAL), ("M2", lead)):
        a, n = agreement(lab, tos, L); rec[f"to_agree_{name}"], rec[f"to_n_{name}"] = a, n
        a, n = agreement(lab, shots, L); rec[f"shot_agree_{name}"], rec[f"shot_n_{name}"] = a, n
    rec["to_curve"] = [list(agreement(lab, tos, L)) for L in LEAD_GRID]
    json.dump(rec, open(out, "w")); return rec


def stage_events(workers: int) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    T = pd.read_csv(SHARED, dtype={"game_id": str}); T = T[T.quality_status == "CALIBRATED"]
    pbp = pd.read_parquet(PBP); pbp["gameId"] = pbp.gameId.astype(str).str.zfill(10)
    jobs = [(r.game_id, r.stem, float(r.calibrated_lead_s), pbp[pbp.gameId == r.game_id].to_dict("records")) for r in T.itertuples() if not (CACHE / f"{r.game_id}.json").exists()]
    print(f"[events] games to do {len(jobs)} of {len(T)}", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, fu in enumerate(as_completed([ex.submit(game_events, j) for j in jobs])):
            fu.result()
            if (i + 1) % 50 == 0:
                print(f"[events] {i + 1}/{len(jobs)}", flush=True)
    return 0


def stage_screens() -> int:
    """detected on-ball screens on validated games: possession under each lead; onset after span start."""
    SC = Path(os.environ.get("SCREEN_PROJECT_DIR", "data/derived/screen")); import yaml; from screen_candidate_mask import candidate_mask  # noqa: E402  (withheld intermediates; see docs/REPRODUCIBILITY.md)
    T = pd.read_csv(SHARED, dtype={"game_id": str}); lead = T[T.lead_status == "CLOCK_CALIBRATION_VALIDATED"].set_index("game_id").calibrated_lead_s.to_dict()
    scr = pd.read_parquet(SC / "data" / "screens_v3.parquet", columns=["screen_id", "game_id", "possession_id", "period", "t0_game_clock"])
    fe = pd.read_parquet(SC / "data" / "screen_geometry_features_v3.parquet"); cand = next(c for c in yaml.safe_load((SC / "configs" / "sc_a02_candidates.yaml").read_text())["candidates"] if c["id"] == "C15")
    scr = scr[scr.screen_id.isin(fe[candidate_mask(fe, cand)].screen_id) & scr.game_id.isin(lead)]
    v3 = pd.read_parquet(SC / "data" / "v3_possession_inventory.parquet", columns=["game_id", "possession_id", "period", "span_start", "span_end"]); v3 = v3[v3.game_id.isin(scr.game_id.unique())]
    v3["lo"] = v3[["span_start", "span_end"]].min(axis=1); v3["hi"] = v3[["span_start", "span_end"]].max(axis=1); idx = {k: g.sort_values("hi") for k, g in v3.groupby(["game_id", "period"])}; span = v3.set_index("possession_id")
    rows = []
    for r in scr.itertuples():
        g = idx.get((r.game_id, int(r.period))); rec = {"screen_id": r.screen_id, "game_id": r.game_id}
        for name, L in (("M0", 0.0), ("M1", GLOBAL), ("M2", lead[r.game_id])):
            t = float(r.t0_game_clock) - L; cand = g[(g.lo < t) & (t <= g.hi)] if g is not None else None
            pid = cand.possession_id.iloc[0] if cand is not None and len(cand) else None
            rec[f"pid_{name}"] = pid; rec[f"onset_{name}"] = (float(span.loc[pid, "hi"]) + L) - float(r.t0_game_clock) if pid is not None else np.nan
        rows.append(rec)
    S = pd.DataFrame(rows); S.to_parquet(R / "data" / "global_shift_screens.parquet", index=False)
    out = {"n_screens": int(len(S)), "n_games": int(S.game_id.nunique())}
    for name in ("M0", "M1", "M2"):
        x = S[f"onset_{name}"].dropna(); out[name] = {"frac_onset_lt_0.5s": float((x < 0.5).mean()), "frac_onset_lt_0.25s": float((x < 0.25).mean()), "median_onset_s": float(x.median()), "n_with_possession": int(len(x)),
                                                  "reassigned_vs_M0": float(((S[f"pid_{name}"] != S.pid_M0) & S[f"pid_{name}"].notna() & S.pid_M0.notna()).mean()), "no_possession_frac": float(S[f"pid_{name}"].isna().mean())}
    json.dump(out, open(R / "results" / "global_shift_screens.json", "w"), indent=2); print(json.dumps(out, indent=1)); return 0


def stage_report() -> int:
    T = pd.read_csv(SHARED, dtype={"game_id": str}); tax = pd.read_csv(TAX, dtype={"game_id": str}).set_index("game_id").taxonomy_class.to_dict()
    recs = [json.load(open(f)) for f in sorted(CACHE.glob("*.json"))]; G = pd.DataFrame([{k: v for k, v in r.items() if k != "to_curve"} for r in recs])
    G["taxonomy_class"] = G.game_id.map(tax); G["lead_status"] = G.game_id.map(T.set_index("game_id").lead_status)
    for name in ("M0", "M1", "M2"):
        G[f"to_rate_{name}"] = G[f"to_agree_{name}"] / G[f"to_n_{name}"].replace(0, np.nan); G[f"shot_rate_{name}"] = G[f"shot_agree_{name}"] / G[f"shot_n_{name}"].replace(0, np.nan)
    G["to_M2_minus_M1"] = G.to_rate_M2 - G.to_rate_M1; G.to_csv(R / "results" / "global_shift_by_game.csv", index=False)
    def stats(g, name):
        x = g[f"to_rate_{name}"].dropna(); dec = x.sort_values().iloc[: max(1, int(np.ceil(len(x) / 10)))]
        return {"pooled": float(g[f"to_agree_{name}"].sum() / g[f"to_n_{name}"].sum()), "n_events": int(g[f"to_n_{name}"].sum()), "n_games": int(len(x)), "median": float(x.median()), "p05": float(x.quantile(.05)), "p25": float(x.quantile(.25)), "p75": float(x.quantile(.75)), "p95": float(x.quantile(.95)),
                "frac_ge_0.90": float((x >= 0.90).mean()), "frac_ge_0.95": float((x >= 0.95).mean()), "worst_decile_mean": float(dec.mean()), "shot_wrong_team_rate": float(1 - g[f"shot_agree_{name}"].sum() / g[f"shot_n_{name}"].sum()), "turnover_wrong_team_rate": float(1 - g[f"to_agree_{name}"].sum() / g[f"to_n_{name}"].sum())}
    out = {"universe": {"all_calibratable": {m: stats(G, m) for m in ("M0", "M1", "M2")}, "validated_only": {m: stats(G[G.lead_status == "CLOCK_CALIBRATION_VALIDATED"], m) for m in ("M0", "M1", "M2")}}}
    imp = {}
    for cls, g in [("ALL", G)] + [(c, G[G.taxonomy_class == c]) for c in CLASSES]:
        d = g.to_M2_minus_M1.dropna(); imp[cls] = {"n_games": int(len(d)), "pooled_M1": float(g.to_agree_M1.sum() / g.to_n_M1.sum()), "pooled_M2": float(g.to_agree_M2.sum() / g.to_n_M2.sum()), "pooled_M2_minus_M1": float(g.to_agree_M2.sum() / g.to_n_M2.sum() - g.to_agree_M1.sum() / g.to_n_M1.sum()),
                                                    "per_game_mean_diff": float(d.mean()), "per_game_median_diff": float(d.median()), "frac_games_M2_better": float((d > 0).mean()), "frac_games_M1_better": float((d < 0).mean()), "frac_games_M1_lt_0.90": float((g.to_rate_M1 < 0.90).mean()), "frac_games_M2_lt_0.90": float((g.to_rate_M2 < 0.90).mean()),
                                                    "lead_abs_dev_from_4_median": float((g.lead - GLOBAL).abs().median())}
    out["M2_minus_M1"] = imp; out["screens"] = json.load(open(R / "results" / "global_shift_screens.json"))
    json.dump(out, open(R / "results" / "global_shift_summary.json", "w"), indent=2)
    U = out["universe"]; sc = out["screens"]
    md = ["# GLOBAL +4 s vs PER-GAME calibration (rules frozen before the results; producer src/global_shift.py)", "",
          "Primary evaluation: held-out turnover-team agreement (never used to choose a lead). M1 = +4.0 s is the only global offset evaluated (the previously observed corpus median).", ""]
    for uni, lab in (("all_calibratable", "All 631 calibratable games"), ("validated_only", "CLOCK_CALIBRATION_VALIDATED games (437)")):
        md += [f"## {lab}", "", "| method | pooled agreement | n turnovers | per-game median | p05 | p25 | p75 | p95 | games ≥ 0.90 | games ≥ 0.95 | worst-decile mean |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for m, nm in (("M0", "M0 naive 0 s"), ("M1", "M1 global +4.0 s"), ("M2", "M2 per-game")):
            s = U[uni][m]; md.append(f"| {nm} | **{s['pooled']:.3f}** | {s['n_events']:,} | {s['median']:.3f} | {s['p05']:.3f} | {s['p25']:.3f} | {s['p75']:.3f} | {s['p95']:.3f} | {s['frac_ge_0.90']*100:.1f} % | {s['frac_ge_0.95']*100:.1f} % | {s['worst_decile_mean']:.3f} |")
        md.append("")
    md += ["## Secondary structural metrics (validated games for screens; all calibratable for windows)", "", "| metric | M0 naive | M1 global +4 s | M2 per-game |", "|---|---|---|---|",
           f"| 1. shot-window wrong-team rate | {U['all_calibratable']['M0']['shot_wrong_team_rate']:.3f} | {U['all_calibratable']['M1']['shot_wrong_team_rate']:.3f} | {U['all_calibratable']['M2']['shot_wrong_team_rate']:.3f} |",
           f"| 2. turnover-window wrong-team rate | {U['all_calibratable']['M0']['turnover_wrong_team_rate']:.3f} | {U['all_calibratable']['M1']['turnover_wrong_team_rate']:.3f} | {U['all_calibratable']['M2']['turnover_wrong_team_rate']:.3f} |",
           f"| 3. apparent screen onset < 0.5 s ({sc['n_screens']:,} detected on-ball screens, {sc['n_games']} games) | {sc['M0']['frac_onset_lt_0.5s']*100:.1f} % | {sc['M1']['frac_onset_lt_0.5s']*100:.1f} % | {sc['M2']['frac_onset_lt_0.5s']*100:.1f} % |",
           f"| 4. screen possession reassignment vs M0 | — | {sc['M1']['reassigned_vs_M0']*100:.1f} % | {sc['M2']['reassigned_vs_M0']*100:.1f} % |",
           f"| median screen onset (s) | {sc['M0']['median_onset_s']:.2f} | {sc['M1']['median_onset_s']:.2f} | {sc['M2']['median_onset_s']:.2f} |", "",
           "## M2 − M1 (held-out turnovers) overall and by frozen taxonomy class", "", "| class | games | pooled M1 | pooled M2 | pooled M2−M1 | per-game mean diff | per-game median diff | games M2 better | games M1 better | games M1 < 0.90 | games M2 < 0.90 | median |lead − 4| |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cls in ["ALL"] + CLASSES:
        i = imp[cls]; md.append(f"| {cls} | {i['n_games']} | {i['pooled_M1']:.3f} | {i['pooled_M2']:.3f} | **{i['pooled_M2_minus_M1']:+.3f}** | {i['per_game_mean_diff']:+.3f} | {i['per_game_median_diff']:+.3f} | {i['frac_games_M2_better']*100:.1f} % | {i['frac_games_M1_better']*100:.1f} % | {i['frac_games_M1_lt_0.90']*100:.1f} % | {i['frac_games_M2_lt_0.90']*100:.1f} % | {i['lead_abs_dev_from_4_median']:.1f} s |")
    md += ["", "Reading rule (frozen): M1 is judged only on held-out turnovers; no spacing/eFG/Timeout quantity was consulted."]
    (R / "audit" / "GLOBAL_SHIFT_BASELINE.md").write_text("\n".join(md) + "\n"); print(json.dumps({"universe": U, "M2_minus_M1": imp}, indent=1)); return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=["events", "screens", "report"], required=True); ap.add_argument("--workers", type=int, default=16); a = ap.parse_args()
    raise SystemExit({"events": lambda: stage_events(a.workers), "screens": stage_screens, "report": stage_report}[a.stage]())
