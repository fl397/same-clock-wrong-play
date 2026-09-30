#!/usr/bin/env python3
"""Spacing–eFG comparison, naive vs corrected join (descriptive; NOT a separate contribution).
Reproduces the external repository's spacing-at-shot comparison (ismayc/tracking-study 06_possession_join.py) on all
CLOCK_CALIBRATION_VALIDATED games: spacing = mean convex-hull area of the shooting team's five players over the frames in
[c + lead, c + lead + 2 s] (calibrated) or [c, c + 2 s] (naive, lead 0) that the nearest-player heuristic labels as that
team's possession (>= 5 frames); eFG% and 3PA share by spacing quartile (quartiles over all joined shots).
Implementation on the npz layer: nearest player to ball <= 4 ft with ball z <= 10 ft (same rule as the source heuristic).
Writes results/external_artifact_generalization.csv and audit/EXTERNAL_ARTIFACT_GENERALIZATION.md.
"""
from __future__ import annotations
import json, re
import os
from pathlib import Path
import numpy as np, pandas as pd
from scipy.spatial import ConvexHull

R = Path(__file__).resolve().parents[1]; SH = R / "results"; NPZ = Path(os.environ.get("NPZ_DIR", "data/derived/possessions"))
PBP = os.environ.get("PBP_PARQUET", "data/external/pbp/2015-16/all.parquet"); LOOK, MINF = 2.0, 5


def parse_clock(s):
    m = re.match(r"PT(\d+)M([\d.]+)S", str(s)); return float(m.group(1)) * 60 + float(m.group(2)) if m else np.nan


def hull(xy):
    try:
        return float(ConvexHull(xy).volume)
    except Exception:
        return np.nan


def main() -> int:
    T = pd.read_csv(SH / "clock_alignment_v1.csv", dtype={"game_id": str}); V = T[T.lead_status == "CLOCK_CALIBRATION_VALIDATED"]
    pbp = pd.read_parquet(PBP); pbp["gid"] = pbp.gameId.astype(str).str.zfill(10); pbp = pbp[pbp.gid.isin(V.game_id) & (pbp.isFieldGoal.astype(str) == "1")].copy()
    pbp["secs"] = pbp.clock.map(parse_clock); pbp["team"] = pd.to_numeric(pbp.teamId, errors="coerce").fillna(0).astype(int); pbp = pbp[(pbp.team != 0) & pbp.secs.notna()]
    cache = R / "data" / "spacing_at_shot_generalization.parquet"
    if cache.exists():
        S = pd.read_parquet(cache)
    else:
        rows = []
        for r in V.itertuples():
            f = NPZ / f"{r.stem}.npz"
            if not f.exists():
                continue
            d = np.load(f, allow_pickle=True)
            if "game_clock" not in d.files:
                continue
            gc = d["game_clock"]; per = np.repeat(d["quarters"], np.diff(d["offsets"])); ball = d["ball_xyz"]; pxy = d["player_xy"]; tid = d["team_ids"]
            slot_team = np.repeat(np.concatenate([np.repeat(tid[:, :1], 5, 1), np.repeat(tid[:, 1:], 5, 1)], 1), np.diff(d["offsets"]), axis=0)  # (T,10)
            dist = np.linalg.norm(pxy - ball[:, None, :2], axis=-1); dist = np.where(np.isnan(dist), np.inf, dist); near = dist.argmin(1); ok = (dist[np.arange(len(dist)), near] <= 4.0) & (ball[:, 2] <= 10.0)
            off_team = np.where(ok, slot_team[np.arange(len(near)), near], -1)
            # hull of the possessing team's five players, computed only on frames inside shot windows (cached by frame index)
            hcache = {}
            def hull_at(i):
                if i not in hcache:
                    sel = slot_team[i] == off_team[i]
                    hcache[i] = hull(pxy[i, sel]) if (sel.sum() == 5 and not np.isnan(pxy[i, sel]).any()) else np.nan
                return hcache[i]
            g = pbp[pbp.gid == r.game_id]
            for e in g.itertuples():
                for lab, lead in (("calibrated", r.calibrated_lead_s), ("naive", 0.0)):
                    lo = e.secs + lead; idx = np.where((per == e.period) & (gc >= lo) & (gc <= lo + LOOK) & (off_team == e.team))[0]
                    hv = np.array([hull_at(i) for i in idx]); hv = hv[~np.isnan(hv)]
                    if len(hv) >= MINF:
                        rows.append({"game_id": r.game_id, "axis": lab, "period": e.period, "secs": e.secs, "hull_area": float(hv.mean()), "made": e.shotResult == "Made", "shot_value": int(e.shotValue)})
            print(r.game_id, len(rows), flush=True)
        S = pd.DataFrame(rows); S.to_parquet(cache, index=False)
    out = []
    for lab, g in S.groupby("axis"):
        qs = g.hull_area.quantile([.25, .5, .75]).values; q = np.digitize(g.hull_area, qs)
        for k in range(4):
            x = g[q == k]; efg = (x.made.sum() + 0.5 * (x.made & (x.shot_value == 3)).sum()) / len(x)
            out.append({"axis": lab, "quartile": f"Q{k+1}", "n": len(x), "mean_hull_sqft": x.hull_area.mean(), "efg": efg, "share_3pt": (x.shot_value == 3).mean()})
    O = pd.DataFrame(out); O.to_csv(R / "results" / "external_artifact_generalization.csv", index=False)
    md = ["# Spacing–eFG comparison, naive vs corrected join (descriptive only; not a separate contribution)", "",
          f"Source definition reproduced on {S.game_id.nunique()} validated games ({int((S.axis=='calibrated').sum()):,} calibrated / {int((S.axis=='naive').sum()):,} naive joined shots). Spacing = mean hull area of the shooting team's five players over labelled frames in the 2-s window at the calibrated lead vs at lead 0.", "",
          "| axis | quartile | n | mean hull (sq ft) | eFG% | 3PA share |", "|---|---|---|---|---|---|"] + [f"| {r.axis} | {r.quartile} | {r.n:,} | {r.mean_hull_sqft:.0f} | {r.efg:.3f} | {r.share_3pt:.3f} |" for r in O.itertuples()]
    md += ["", "Reading: the uncalibrated join samples a window that mostly belongs to the *next* possession, so its 'spacing at the shot' is a mixture; the calibrated join samples the shooting team's set-up. Any gradient difference between the two rows is an alignment artefact, as the external repository reported for 10 games. This table is descriptive and feeds no confirmatory analysis."]
    (R / "audit" / "EXTERNAL_ARTIFACT_GENERALIZATION.md").write_text("\n".join(md) + "\n"); print(O.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
