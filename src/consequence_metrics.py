#!/usr/bin/env python3
"""structural consequences of naive vs calibrated timing (rules frozen in configs/CONSEQUENCE_METRICS.yaml).
Validated games only. No basketball outcome, no TSS, no treatment effect.
Inputs (read-only): results/clock_alignment_v1.csv; main-repo per-game JSON (eventid diag); raw SportVU JSON for an exact
40-game subsample of the PBP-event label change (the calibration engine is imported unchanged); screens_v3 + v3 possession
spans; timeout windows + npz frames. Outputs: results/consequence_*.csv, audit/CONSEQUENCE_METRICS.md, data/*.parquet (withheld).
"""
from __future__ import annotations
import glob, json, sys
import os
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]; SH = R / "results"
MAIN = Path(os.environ.get("PROJECT_ROOT", ".")); TS = Path(os.environ.get("TIMEOUT_PROJECT_DIR", "data/derived/timeout")); SC = Path(os.environ.get("SCREEN_PROJECT_DIR", "data/derived/screen"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clock_latency_calibration import frames_from_events, possession_frames, Labeler, load_pbp, agreement, LOOKBACK_S  # noqa: E402
P075 = Path(os.environ.get("V3_DIR", "data/derived/phase0_75")); NPZ = Path(os.environ.get("NPZ_DIR", "data/derived/possessions")); RAW = Path(os.environ.get("SPORTVU_JSON_DIR", "data/external/sportvu/json"))
SEED, N_SUB = 20260919, 40


def main() -> int:
    T = pd.read_csv(SH / "clock_alignment_v1.csv", dtype={"game_id": str}); V = T[T.lead_status == "CLOCK_CALIBRATION_VALIDATED"].copy(); lead = V.set_index("game_id").calibrated_lead_s.to_dict()
    out = {"n_validated_games": int(len(V))}
    # ---------- B: event-relative time error (= lead per event) + eventId relation ----------
    ev_rows = []
    for r in V.itertuples():
        j = json.load(open(Path(os.environ.get("LATENCY_GAMES_DIR", "data/derived/latency_all_games/games")) / f"{r.game_id}.json")); d = j["eventid_diag"]
        ev_rows.append({"game_id": r.game_id, "lead": r.calibrated_lead_s, "shots": r.shot_n_calibrated, "turnovers": r.to_n_calibrated, "shots_eventid_matched": d["shots"]["eventid_matched"], "shots_eventid_n": d["shots"]["n"], "shots_container_overlap": d["shots"]["container_overlaps_calibrated_window"],
                        "to_eventid_matched": d["turnovers"]["eventid_matched"], "to_eventid_n": d["turnovers"]["n"], "to_container_overlap": d["turnovers"]["container_overlaps_calibrated_window"]})
    E = pd.DataFrame(ev_rows)
    def wq(vals, w, p): o = np.argsort(vals); cv = np.cumsum(w[o]) / w.sum(); return float(vals[o][np.searchsorted(cv, p / 100)])
    B = {}
    for kind in ("shots", "turnovers"):
        w = E[kind].values.astype(float); v = E.lead.values
        B[kind] = {"n_events": int(w.sum()), "abs_error_p05": wq(v, w, 5), "abs_error_p25": wq(v, w, 25), "abs_error_p50": wq(v, w, 50), "abs_error_p75": wq(v, w, 75), "abs_error_p95": wq(v, w, 95), "abs_error_mean": float((v * w).sum() / w.sum()),
                   "frac_error_ge_2s": float(w[v >= 2.0].sum() / w.sum()), "frac_error_ge_4s": float(w[v >= 4.0].sum() / w.sum())}
    B["eventid"] = {"shots_matched_frac": float(E.shots_eventid_matched.sum() / E.shots_eventid_n.sum()), "shots_container_overlap_frac_of_matched": float(E.shots_container_overlap.sum() / E.shots_eventid_matched.sum()),
                    "to_matched_frac": float(E.to_eventid_matched.sum() / E.to_eventid_n.sum()), "to_container_overlap_frac_of_matched": float(E.to_container_overlap.sum() / E.to_eventid_matched.sum())}
    out["B"] = B; E.to_csv(R / "results" / "consequence_B_events_by_game.csv", index=False)
    # ---------- A (PBP events): agreement-based bounds on all validated games + exact label change on a 40-game subsample ----------
    A = {}
    for kind, na, nr, ca, cn in (("shots", "shot_rate_naive", "shot_n_naive", "shot_agree_calibrated", "shot_n_calibrated"), ("turnovers", "to_rate_naive", "to_n_naive", "to_agree_calibrated", "to_n_calibrated")):
        naive_dis = 1 - (V[na] * V[nr]).sum() / V[nr].sum(); cal_dis = 1 - V[ca].sum() / V[cn].sum()
        A[kind] = {"naive_team_disagreement": float(naive_dis), "calibrated_team_disagreement": float(cal_dis), "change_fraction_lower_bound": float(naive_dis - cal_dis), "change_fraction_upper_bound": float(min(1.0, naive_dis + cal_dis))}
    rng = np.random.default_rng(SEED); sub = sorted(rng.choice(V.game_id.values, size=N_SUB, replace=False)); pbp = pd.read_parquet(os.environ.get("PBP_PARQUET", "data/external/pbp/2015-16/all.parquet"))
    stem = V.set_index("game_id").stem.to_dict(); ch = {"shots": [0, 0, 0], "turnovers": [0, 0, 0]}   # [changed, both_labelled, naive_unlabelled->labelled]
    cache = R / "data" / "label_change_subsample.json"
    if cache.exists():
        ch = json.load(open(cache))["counts"]
    else:
        for gid in sub:
            g = json.load(open(RAW / f"{stem[gid]}.json")); fr, _ = frames_from_events(g["events"]); poss = possession_frames(fr); lab = Labeler(poss)
            p = load_pbp(pbp[pbp.gameId.astype(str) == gid]); shots = p[p.is_fga & (p.team_id != 0)]; tos = p[p.is_turnover & (p.team_id != 0)]
            for kind, evs in (("shots", shots), ("turnovers", tos)):
                for e in evs.itertuples():
                    l0 = lab.label(int(e.period), float(e.secs_left), 0.0); l1 = lab.label(int(e.period), float(e.secs_left), lead[gid])
                    if l0 is not None and l1 is not None:
                        ch[kind][1] += 1; ch[kind][0] += int(l0 != l1)
                    elif l0 is None and l1 is not None:
                        ch[kind][2] += 1
            print("subsample", gid, ch, flush=True)
        json.dump({"games": sub, "counts": ch}, open(cache, "w"))
    for kind in ("shots", "turnovers"):
        A[kind]["subsample_40_games_exact_change_fraction"] = ch[kind][0] / max(ch[kind][1], 1); A[kind]["subsample_n_events_both_labelled"] = ch[kind][1]; A[kind]["subsample_naive_unlabelled_calibrated_labelled"] = ch[kind][2]
    # ---------- A (screens) + C ----------
    scr = pd.read_parquet(SC / "data" / "screens_v3.parquet", columns=["screen_id", "game_id", "possession_id", "period", "t0_game_clock"])
    import yaml; from screen_candidate_mask import candidate_mask  # noqa: E402  (vendored screen-candidate definition, unchanged)
    fe = pd.read_parquet(SC / "data" / "screen_geometry_features_v3.parquet"); cand = next(c for c in yaml.safe_load((SC / "configs" / "sc_a02_candidates.yaml").read_text())["candidates"] if c["id"] == "C15")
    scr = scr[scr.screen_id.isin(fe[candidate_mask(fe, cand)].screen_id) & scr.game_id.isin(lead)]
    # The screen-detection possession objects are the possession spans (previous terminal clock -> own terminal clock), NOT the raw v3 start/end
    v3 = pd.read_parquet(SC / "data" / "v3_possession_inventory.parquet", columns=["game_id", "possession_id", "period", "span_start", "span_end"]); v3 = v3[v3.game_id.isin(scr.game_id.unique())]
    v3["lo"] = v3[["span_start", "span_end"]].min(axis=1); v3["hi"] = v3[["span_start", "span_end"]].max(axis=1)
    idx = {k: g.sort_values("hi") for k, g in v3.groupby(["game_id", "period"])}
    span = v3.set_index("possession_id")
    rows = []
    for r in scr.itertuples():
        ell = lead[r.game_id]; t_pbp = float(r.t0_game_clock) - ell   # tracking instant mapped to the PBP axis
        g = idx.get((r.game_id, int(r.period)))
        cand = g[(g.lo < t_pbp) & (t_pbp <= g.hi)] if g is not None else g
        cal_pid = cand.possession_id.iloc[0] if cand is not None and len(cand) else None
        naive_start = float(span.loc[r.possession_id, "hi"]) if r.possession_id in span.index else np.nan
        cal_start = float(span.loc[cal_pid, "hi"]) if cal_pid is not None else np.nan
        rows.append({"screen_id": r.screen_id, "game_id": r.game_id, "lead": ell, "naive_pid": r.possession_id, "cal_pid": cal_pid, "changed": (cal_pid is not None) and (cal_pid != r.possession_id), "no_cal_possession": cal_pid is None,
                     "onset_naive_s": naive_start - float(r.t0_game_clock), "onset_cal_s": (cal_start + ell) - float(r.t0_game_clock) if cal_pid is not None else np.nan, "n_candidates": 0 if cand is None else len(cand)})
    S = pd.DataFrame(rows); S.to_parquet(R / "data" / "screen_reassignment.parquet", index=False)
    A["screens"] = {"n_events": int(len(S)), "n_games": int(S.game_id.nunique()), "changed_fraction": float(S.changed.mean()), "no_calibrated_possession_fraction": float(S.no_cal_possession.mean()), "ambiguous_multi_candidate_fraction": float((S.n_candidates > 1).mean())}
    out["A"] = A
    C = {}
    for lab_, col in (("naive", "onset_naive_s"), ("calibrated", "onset_cal_s")):
        x = S[col].dropna(); C[lab_] = {"n": int(len(x)), "median_onset_s": float(x.median()), "p10": float(x.quantile(.1)), "p90": float(x.quantile(.9)), "frac_lt_0.25s": float((x < 0.25).mean()), "frac_lt_0.5s": float((x < 0.5).mean()), "frac_lt_1.0s": float((x < 1.0).mean()), "frac_negative": float((x < 0).mean())}
    out["C"] = C
    # ---------- D: window membership change (frames) ----------
    wins = pd.read_parquet(os.environ.get("TIMEOUT_WINDOWS_PARQUET", "data/derived/v3_timeout_windows.parquet")); wins["game_id"] = wins.game_id.astype(str).str.zfill(10); wins = wins[wins.game_id.isin(lead)]
    allv3 = pd.read_parquet(P075 / "possessions_v3.parquet", columns=["game_id", "possession_id", "period", "start_clock_seconds", "end_clock_seconds"]).set_index("possession_id")
    npz_by_game = {}
    for f in NPZ.glob("*.npz"):
        d = np.load(f, allow_pickle=True)
        if "game_id" in d.files and "game_clock" in d.files:
            npz_by_game[str(d["game_id"])] = f
    drows = []
    for gid, gw in wins.groupby("game_id"):
        if gid not in npz_by_game:
            continue
        d = np.load(npz_by_game[gid], allow_pickle=True); gc = d["game_clock"]; per = np.repeat(d["quarters"], np.diff(d["offsets"])); ell = lead[gid]
        for w in gw.itertuples():
            for col in ("pre_offense_possession_ids", "post_offense_possession_ids", "pre_defense_possession_ids", "post_defense_possession_ids"):
                for pid in json.loads(getattr(w, col)):
                    if pid not in allv3.index:
                        continue
                    p = allv3.loc[pid]; lo, hi = float(min(p.start_clock_seconds, p.end_clock_seconds)), float(max(p.start_clock_seconds, p.end_clock_seconds)); m = per == int(p.period)
                    naive = m & (gc >= lo) & (gc <= hi); cal = m & (gc >= lo + ell) & (gc <= hi + ell); n_naive = int(naive.sum())
                    drows.append({"observation_id": w.observation_id, "game_id": gid, "possession_id": pid, "zero_span": lo == hi, "n_naive": n_naive, "n_cal": int(cal.sum()), "n_both": int((naive & cal).sum())})
    D = pd.DataFrame(drows); D.to_parquet(R / "data" / "window_membership.parquet", index=False)
    def dsum(x):
        n = x.n_naive.sum(); return {"member_possessions": int(len(x)), "frames_naive": int(n), "frames_leaving_fraction": float(1 - x.n_both.sum() / max(n, 1)), "frames_calibrated": int(x.n_cal.sum())}
    Dd = {"all": dsum(D), "zero_span": dsum(D[D.zero_span]), "positive_span": dsum(D[~D.zero_span]), "n_windows": int(D.observation_id.nunique()), "n_games": int(D.game_id.nunique())}
    W = D.groupby("observation_id").agg(n_naive=("n_naive", "sum"), n_both=("n_both", "sum")); W = W[W.n_naive > 0]; chg = 1 - W.n_both / W.n_naive
    Dd["windows_change_gt_25pct"] = float((chg > 0.25).mean()); Dd["windows_change_gt_50pct"] = float((chg > 0.5).mean()); Dd["windows_median_change"] = float(chg.median())
    out["D"] = Dd
    json.dump(out, open(R / "results" / "consequence_metrics.json", "w"), indent=2)
    md = ["# Structural consequences of naive vs calibrated timing (rules: configs/CONSEQUENCE_METRICS.yaml)", "", f"Validated games: {out['n_validated_games']}. No basketball outcome is reported.", "",
          "## A. Possession / team-assignment change", "", "| event type | naive team disagreement | calibrated | change fraction (bounds, all validated games) | exact change fraction (40-game random subsample, seed 20260919) | n events (subsample) |", "|---|---|---|---|---|---|"]
    for k in ("shots", "turnovers"):
        a = A[k]; md.append(f"| {k} | {a['naive_team_disagreement']:.3f} | {a['calibrated_team_disagreement']:.3f} | {a['change_fraction_lower_bound']:.3f} – {a['change_fraction_upper_bound']:.3f} | **{a['subsample_40_games_exact_change_fraction']:.3f}** | {a['subsample_n_events_both_labelled']:,} (+{a['subsample_naive_unlabelled_calibrated_labelled']} naive-unlabelled) |")
    s = A["screens"]; md += ["", f"Screens (existing detected on-ball screen events, {s['n_events']:,} events in {s['n_games']} validated games): **{s['changed_fraction']*100:.1f} %** are assigned to a different v3 possession once the tracking clock is mapped to the PBP axis with the calibrated lead; {s['no_calibrated_possession_fraction']*100:.1f} % fall into a gap between possessions; {s['ambiguous_multi_candidate_fraction']*100:.1f} % had more than one candidate (first taken).", "",
          "## B. Event-relative time error (|calibrated − naive| tracking instant = per-game lead)", "", "| events | n | p05 | p25 | p50 | p75 | p95 | mean | ≥ 2 s | ≥ 4 s |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("shots", "turnovers"):
        b = B[k]; md.append(f"| {k} | {b['n_events']:,} | {b['abs_error_p05']:.1f} | {b['abs_error_p25']:.1f} | {b['abs_error_p50']:.1f} | {b['abs_error_p75']:.1f} | {b['abs_error_p95']:.1f} | {b['abs_error_mean']:.2f} | {b['frac_error_ge_2s']*100:.1f} % | {b['frac_error_ge_4s']*100:.1f} % |")
    e = B["eventid"]; md += ["", f"SportVU event-container ids match PBP `actionNumber` for {e['shots_matched_frac']*100:.1f} % of shots / {e['to_matched_frac']*100:.1f} % of turnovers; of the matched containers only {e['shots_container_overlap_frac_of_matched']*100:.1f} % / {e['to_container_overlap_frac_of_matched']*100:.1f} % have a clock span overlapping the calibrated label window — the id join does not remove the clock offset.", "",
          "## C. Early-possession misclassification (detected on-ball screens: onset after possession start)", "", "| axis | n | median onset (s) | p10 | p90 | < 0.25 s | < 0.5 s | < 1.0 s | negative |", "|---|---|---|---|---|---|---|---|---|"]
    for k in ("naive", "calibrated"):
        c = C[k]; md.append(f"| {k} | {c['n']:,} | {c['median_onset_s']:.2f} | {c['p10']:.2f} | {c['p90']:.2f} | {c['frac_lt_0.25s']*100:.1f} % | {c['frac_lt_0.5s']*100:.1f} % | {c['frac_lt_1.0s']*100:.1f} % | {c['frac_negative']*100:.1f} % |")
    md += ["", "## D. Window membership change (existing timeout windows; tracking frames)", "", "| population | member possessions | naive frames | fraction of naive frames leaving the window | calibrated frames |", "|---|---|---|---|---|"]
    for k in ("all", "zero_span", "positive_span"):
        x = Dd[k]; md.append(f"| {k} | {x['member_possessions']:,} | {x['frames_naive']:,} | **{x['frames_leaving_fraction']*100:.1f} %** | {x['frames_calibrated']:,} |")
    md += ["", f"Windows: {Dd['n_windows']:,} in {Dd['n_games']} games; median per-window change {Dd['windows_median_change']*100:.1f} %; windows changing > 25 %: {Dd['windows_change_gt_25pct']*100:.1f} %, > 50 %: {Dd['windows_change_gt_50pct']*100:.1f} %.",
           "Zero-span rows are v3 possessions with identical start and end clock; their naive frames are stopped-clock frames at one clock value and vanish under any shift (the live-play analysis characterises them)."]
    (R / "audit" / "CONSEQUENCE_METRICS.md").write_text("\n".join(md) + "\n"); print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
