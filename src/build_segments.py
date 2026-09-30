#!/usr/bin/env python3
"""full-corpus semantic segment table + frozen M1/M2/M3 under NAIVE vs LIVE_PLAY_ONLY.

Implements configs/LIVE_PLAY_CLASSIFIER.yaml v1 (frozen before any comparison) literally. One process per game
(multiprocessing), per-game parquet cache in data/cache/, resume-safe. Writes
  data/segments_semantic.parquet        one row per v3 possession row in the universe (WITHHOLD_PENDING_RIGHTS)
  data/frames_class_counts.parquet      per game: frame counts by live/non-live reason
  results/universe_games.csv, results/segments_summary.json
No prevalence or distortion statistic is computed here (see prevalence.py / distortion.py).
"""
from __future__ import annotations
import argparse, glob, json, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
from scipy.spatial import ConvexHull, QhullError

R = Path(__file__).resolve().parents[1]
SHARED = R / "results" / "clock_alignment_v1.csv"
JSON_DIR = os.environ.get("SPORTVU_JSON_DIR", "data/external/sportvu/json")
V3 = os.environ.get("V3_POSSESSIONS_PARQUET", "data/derived/possessions_v3.parquet")
PBP = os.environ.get("PBP_WITH_CLOCK_PARQUET", "data/derived/pbp_with_clock.parquet")
CACHE = R / "data" / "cache"
MIN_FRAMES, MAX_DT, MAX_SPEED, STOP_RUN_N, STOP_RUN_S, GAP_S, FLIVE = 25, 0.10, 40.0, 5, 0.20, 0.20, 0.95
ADMIN_TYPES = {"Substitution", "Instant Replay", "Ejection", "Jump Ball", "Foul"}


def load_frames(path: str) -> pd.DataFrame:
    g = json.load(open(path))
    recs, ents = [], []
    for ev in g.get("events") or []:
        for m in ev.get("moments") or []:
            if m[0] is None or m[1] is None or m[2] is None:
                continue
            recs.append((int(m[0]), int(m[1]), float(m[2]), np.nan if m[3] is None else float(m[3]), len(m[5])))
            ents.append(m[5])
    f = pd.DataFrame(recs, columns=["period", "utc", "clock", "shot_clock", "n_ent"])
    f["ent_idx"] = np.arange(len(f))
    f = f.drop_duplicates(["period", "utc"], keep="first").sort_values(["period", "utc"]).reset_index(drop=True)
    return f, ents


def live_flags(f: pd.DataFrame) -> pd.DataFrame:
    """Frame-level live criterion (frozen): running clock, no stopped run, no gap edge, no anomaly."""
    f = f.copy()
    same_period = f.period.eq(f.period.shift())
    dt = (f.utc - f.utc.shift()) / 1000.0
    dc = f.clock - f.clock.shift()
    newrun = (~same_period) | (f.clock != f.clock.shift())
    run_id = newrun.cumsum()
    rs = f.groupby(run_id).agg(n=("utc", "size"), u0=("utc", "min"), u1=("utc", "max"))
    stopped_runs = rs.index[(rs.n >= STOP_RUN_N) | ((rs.u1 - rs.u0) / 1000.0 >= STOP_RUN_S)]
    in_stop = run_id.isin(stopped_runs)
    reason = np.full(len(f), "LIVE", dtype=object)
    reason[in_stop.values] = "STOPPED_CLOCK"
    gap_edge = (~same_period) | (dt > GAP_S)
    reason[(gap_edge & ~in_stop).values] = "GAP_EDGE"
    anomaly = same_period & (dt <= GAP_S) & (dc > 1e-9) & ~in_stop
    reason[anomaly.values] = "CLOCK_ANOMALY"
    # running clock strictly decreasing
    not_dec = same_period & (dt <= GAP_S) & (dc.abs() <= 1e-9) & ~in_stop
    reason[not_dec.values] = "STOPPED_CLOCK"      # short identical-clock pair outside a stopped run: still not running
    f["reason"] = reason
    f["live"] = f.reason == "LIVE"
    f["dt"] = dt
    return f


def frame_metrics(idx: np.ndarray, f: pd.DataFrame, ents: list, offense: int) -> dict:
    """M1/M2/M3 over the frames idx (positions into f). Returns dict with values and usable counts."""
    xy_list, utc_list, keep = [], [], []
    for i in idx:
        e = ents[int(f.ent_idx.iat[i])]
        off = [(x[2], x[3]) for x in e if x[0] == offense]
        ball = [x for x in e if x[0] == -1]
        if len(off) != 5 or not ball:
            continue
        xy_list.append(off); utc_list.append(f.utc.iat[i]); keep.append(i)
    n = len(keep)
    out = {"n_usable": n, "M1": np.nan, "M2": np.nan, "M3": np.nan}
    if n < MIN_FRAMES:
        return out
    xy = np.asarray(xy_list, dtype=float)                       # (n, 5, 2)
    utc = np.asarray(utc_list, dtype=float) / 1000.0
    # M2 hull area, M3 dispersion
    areas = np.empty(n); areas[:] = np.nan
    for k in range(n):
        try:
            areas[k] = ConvexHull(xy[k]).volume
        except (QhullError, ValueError):
            areas[k] = np.nan
    cen = xy.mean(axis=1, keepdims=True)
    disp = np.linalg.norm(xy - cen, axis=2).mean(axis=1)
    # M1 speed between consecutive kept frames with dt <= MAX_DT
    dt = np.diff(utc); ok = (dt > 0) & (dt <= MAX_DT)
    if ok.sum() == 0:
        sp = np.nan
    else:
        d = np.linalg.norm(np.diff(xy, axis=0), axis=2)[ok] / dt[ok][:, None]    # (m, 5)
        d = d[(d <= MAX_SPEED).all(axis=1)]
        sp = float(d.mean()) if len(d) else np.nan
    out.update(M1=sp, M2=float(np.nanmean(areas)), M3=float(disp.mean()))
    return out


def process_game(args) -> str | None:
    stem, gid, lead = args
    outp = CACHE / f"{gid}.parquet"
    if outp.exists():
        return None
    try:
        f, ents = load_frames(f"{JSON_DIR}/{stem}.json")
        if len(f) == 0:
            return f"{gid}: no frames"
        f = live_flags(f)
        v3 = pd.read_parquet(V3); v3 = v3[v3.game_id == gid].copy()
        pbp = pd.read_parquet(PBP); pbp = pbp[pbp.gameId.astype(str) == gid].copy()
        pbp["clock_seconds"] = pd.to_numeric(pbp.clock_seconds, errors="coerce"); pbp = pbp.sort_values("actionNumber")
        pstart = pbp[pbp.actionType.eq("period")].groupby("period").clock_seconds.max().to_dict()
        rows = []
        # frame counts by reason (whole game)
        fc = f.reason.value_counts().to_dict()
        for period, gp in v3.sort_values(["period", "end_actionNumber"]).groupby("period"):
            fp = f[f.period == period].reset_index(drop=True)
            clk = fp.clock.values; live = fp.live.values
            prev_end_clock = float(pstart.get(period, 720.0 if period <= 4 else 300.0)); prev_end_act = -1; prev_term = "PERIOD_START"
            recs = gp.to_dict("records")
            for k, r in enumerate(recs):
                s, e = float(r["start_clock_seconds"]), float(r["end_clock_seconds"])
                a0, a1 = prev_end_act, int(r["end_actionNumber"])
                ev = pbp[(pbp.actionNumber > a0) & (pbp.actionNumber <= a1)]
                types = set(ev.actionType.dropna().astype(str))
                oob_prev = False
                if prev_term == "turnover" and k > 0:
                    pe = pbp[pbp.actionNumber == int(recs[k - 1]["end_actionNumber"])]
                    txt = " ".join(pe.subType.fillna("").astype(str) + " " + pe.description.fillna("").astype(str))
                    oob_prev = "Out of Bounds" in txt
                # interval frames (end+lead, prev_end+lead]
                lo, hi = e + lead, prev_end_clock + lead
                m = (clk > lo) & (clk <= hi)
                idx = np.where(m)[0]; n_naive = len(idx); n_live = int(live[idx].sum()) if n_naive else 0
                f_live = n_live / n_naive if n_naive else np.nan
                reasons = fp.reason.values[idx]
                # row span [end+lead, start+lead]
                rm = (clk >= e + lead - 1e-9) & (clk <= s + lead + 1e-9); ridx = np.where(rm)[0]
                n_row = len(ridx); n_row_stopped = int((fp.reason.values[ridx] == "STOPPED_CLOCK").sum()) if n_row else 0
                # classes
                interval_len = prev_end_clock - e
                if interval_len <= 0 or s > prev_end_clock + 1e-9 or s < e:
                    cls = "SEGMENTATION_ARTIFACT"
                elif n_naive < 5:
                    cls = "AMBIGUOUS"
                elif r["terminal_event"] in ("period_end", "game_end"):
                    cls = "PERIOD_BOUNDARY"
                elif f_live >= FLIVE and n_naive >= MIN_FRAMES:
                    cls = "LIVE_CONTINUOUS_PLAY"
                elif "Timeout" in types:
                    cls = "TIMEOUT"
                elif "Free Throw" in types or prev_term in ("free_throw_made", "interrupted_by_ft"):
                    cls = "FREE_THROW_ADMINISTRATION"
                elif types & ADMIN_TYPES:
                    cls = "SUBSTITUTION_OR_ADMINISTRATION"
                elif oob_prev or "Violation" in types or (prev_term == "turnover" and f_live < FLIVE):
                    cls = "OUT_OF_BOUNDS_OR_INBOUND_SETUP"
                elif prev_term in ("made_shot", "made_shot_and1") and f_live < FLIVE:
                    cls = "MADE_BASKET_DEAD_BALL"
                else:
                    cls = "AMBIGUOUS"
                amb_reason = ("no_tracking" if (cls == "AMBIGUOUS" and n_naive < 5 and interval_len > 0) else "")
                if s < e:
                    rcls = "NEGATIVE_SPAN_ARTIFACT"
                elif s == e:
                    if n_row >= STOP_RUN_N and n_row_stopped >= STOP_RUN_N:
                        rcls = "ZERO_SPAN_STOPPED_BLOCK"
                    elif n_row <= 4 and n_live >= MIN_FRAMES:
                        rcls = "ZERO_CLOCK_SPAN_BUT_TRACKING_MOVEMENT"
                    else:
                        rcls = "ZERO_SPAN_NO_TRACKING"
                else:
                    rcls = "POSITIVE_SPAN"
                offense = int(r["offense_team_id"])
                mn = frame_metrics(idx, fp, ents, offense) if n_naive >= MIN_FRAMES else {"n_usable": 0, "M1": np.nan, "M2": np.nan, "M3": np.nan}
                lidx = idx[live[idx]]
                ml = frame_metrics(lidx, fp, ents, offense) if len(lidx) >= MIN_FRAMES else {"n_usable": 0, "M1": np.nan, "M2": np.nan, "M3": np.nan}
                # movement evidence (supporting only): stationary-frame fraction & ball speed on all interval frames
                utc_span = float((fp.utc.values[idx].max() - fp.utc.values[idx].min()) / 1000.0) if n_naive else np.nan
                sc = fp.shot_clock.values[idx]; sc_prog = float(np.nanmax(sc) - np.nanmin(sc)) if n_naive and np.isfinite(sc).any() else np.nan
                clock_prog = float(clk[idx].max() - clk[idx].min()) if n_naive else np.nan
                rows.append({"game_id": gid, "period": int(period), "possession_id": r["possession_id"], "offense_team_id": offense,
                             "start_clock": s, "end_clock": e, "prev_end_clock": prev_end_clock, "row_span_s": s - e, "interval_s": interval_len,
                             "terminal_event": r["terminal_event"], "preceding_event": prev_term,
                             "following_event": recs[k + 1]["terminal_event"] if k + 1 < len(recs) else "PERIOD_END",
                             "pbp_event_types": "|".join(sorted(types)), "n_pbp_events_in_interval": int(len(ev)),
                             "has_timeout": "Timeout" in types, "has_free_throw": "Free Throw" in types, "has_substitution_or_admin": bool(types & ADMIN_TYPES),
                             "has_oob_or_violation": bool(oob_prev or "Violation" in types), "follows_made_basket": prev_term in ("made_shot", "made_shot_and1"),
                             "n_frames_naive": n_naive, "n_frames_live": n_live, "f_live": f_live,
                             "n_frames_stopped": int((reasons == "STOPPED_CLOCK").sum()), "n_frames_gap_edge": int((reasons == "GAP_EDGE").sum()), "n_frames_anomaly": int((reasons == "CLOCK_ANOMALY").sum()),
                             "utc_span_s": utc_span, "clock_progression_s": clock_prog, "shot_clock_progression_s": sc_prog,
                             "n_row_span_frames": n_row, "n_row_span_stopped": n_row_stopped,
                             "interval_class": cls, "ambiguous_reason": amb_reason, "row_span_class": rcls,
                             "naive_n_usable": mn["n_usable"], "naive_M1": mn["M1"], "naive_M2": mn["M2"], "naive_M3": mn["M3"],
                             "live_n_usable": ml["n_usable"], "live_M1": ml["M1"], "live_M2": ml["M2"], "live_M3": ml["M3"],
                             "lead_s": lead})
                prev_end_clock, prev_end_act, prev_term = e, a1, r["terminal_event"]
        df = pd.DataFrame(rows)
        for k_, v_ in fc.items():
            df[f"game_frames_{k_}"] = v_
        df["game_frames_total"] = len(f)
        df.to_parquet(outp, index=False)
        return None
    except Exception as ex:  # noqa: BLE001
        return f"{gid}: {ex!r}"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    sh = pd.read_csv(SHARED, dtype={"game_id": str})
    v3g = set(pd.read_parquet(V3, columns=["game_id"]).game_id.astype(str))
    u = sh[(sh.lead_status == "CLOCK_CALIBRATION_VALIDATED") & sh.game_id.isin(v3g)].copy()
    u = u[u.stem.map(lambda s: os.path.exists(f"{JSON_DIR}/{s}.json"))]
    u[["game_id", "stem", "calibrated_lead_s"]].to_csv(R / "results" / "universe_games.csv", index=False)
    jobs = [(r.stem, r.game_id, float(r.calibrated_lead_s)) for r in u.itertuples()]
    if a.limit:
        jobs = jobs[: a.limit]
    print(f"universe games {len(u)}; jobs {len(jobs)}", flush=True)
    errs = []
    with Pool(a.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(process_game, jobs)):
            if res:
                errs.append(res); print(res, flush=True)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(jobs)}", flush=True)
    parts = [pd.read_parquet(p) for p in sorted(glob.glob(str(CACHE / "*.parquet")))]
    seg = pd.concat(parts, ignore_index=True); seg.to_parquet(R / "data" / "segments_semantic.parquet", index=False)
    fcols = [c for c in seg.columns if c.startswith("game_frames_")]
    seg.groupby("game_id")[fcols].first().reset_index().to_parquet(R / "data" / "frames_class_counts.parquet", index=False)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=R).decode().strip()
    json.dump({"classifier_version": 1, "classifier_freeze": "frozen before any comparison", "run_head": sha, "n_games": int(seg.game_id.nunique()), "n_segments": int(len(seg)), "errors": errs},
              open(R / "results" / "segments_summary.json", "w"), indent=2)
    print(f"segments {len(seg)} games {seg.game_id.nunique()} errors {len(errs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
