#!/usr/bin/env python3
"""PBP <-> SportVU clock-latency calibration — exact reproduction of ismayc/tracking-study
python/06_possession_join.py (commit d21f8e3c3e7f90c7a9fe16554eafe503565757e2), applied to
our local raw SportVU JSON and PlayByPlayV3 rows.

SIGN CONVENTION (frozen; see test_sign_convention):
    tracking_clock_target = pbp_clock + lead            (both in seconds REMAINING in the period)
    lead > 0  <=>  the play-by-play clock LAGS the tracking clock: a PBP event stamped at
                   600.0 s remaining corresponds to the tracking state at 600.0 + lead s remaining.
    The source's label window for an event is [pbp_clock + lead, pbp_clock + lead + 2.0] on the
    tracking clock; the majority nearest-player team over >= 5 frames is the label.

Per game (source semantics):
  frames      raw moments, de-duplicated on (period, game_clock, player_id) keep-first; ball keyed
              on (period, game_clock) keep-first
  possession  nearest player to the ball within 4.0 ft, ball z <= 10 ft -> off_team per frame
  shots       isFieldGoal == "1" and teamId != 0            (calibration set)
  turnovers   actionType == "Turnover" and teamId != 0      (held-out validation)
  grid        lead in {0.0, 0.5, ..., 8.0}; objective = shot agreement rate; first maximum wins
              (strict >), i.e. ties resolve to the SMALLEST lead
  halves      README-only sensitivity: the same calibration on periods 1-2 and 3-4 separately
  eventId     diagnostic: does the SportVU event container whose eventId equals the PBP actionNumber
              contain the event's clock, and where does it sit relative to the calibrated window
Outputs one JSON per game under <out_dir>/games/<game_id>.json plus inventory fields.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LEAD_GRID = [x * 0.5 for x in range(17)]
LOOKBACK_S = 2.0
MIN_FRAMES = 5
POSSESSION_MAX_DIST = 4.0
POSSESSION_MAX_BALL_Z = 10.0
BALL_ID = -1
RAW = Path(os.environ.get("BASKETBALL_RAW_ROOT", "data/external"))


def tracking_clock_target(pbp_clock: float, lead: float) -> float:
    """The frozen sign convention: tracking clock (s remaining) matching a PBP event clock."""
    return pbp_clock + lead


def test_sign_convention() -> None:
    assert tracking_clock_target(600.0, 4.0) == 604.0, "a PBP event at 600.0 s must map to tracking 604.0 s for lead +4.0"
    assert tracking_clock_target(600.0, 0.0) == 600.0
    lo, hi = tracking_clock_target(600.0, 4.0), tracking_clock_target(600.0, 4.0) + LOOKBACK_S
    assert (lo, hi) == (604.0, 606.0), "label window must lie EARLIER in the period (more seconds remaining)"


def parse_clock(s: str) -> float | None:
    m = re.match(r"PT(\d+)M([\d.]+)S", str(s))
    return float(m.group(1)) * 60 + float(m.group(2)) if m else None


def load_game_json(path: Path) -> tuple[str, list, dict]:
    g = json.loads(path.read_text())
    return str(g["gameid"]), g["events"], g


def frames_from_events(events: list) -> tuple[pd.DataFrame, dict]:
    """Source parse: every moment row (team, player, x, y, z) with period/game_clock; dedup keep-first."""
    per, gc, sc, tid, pid, xs, ys, zs, evid = [], [], [], [], [], [], [], [], []
    n_containers = len(events); n_moments_raw = 0
    for ev in events:
        eid = ev.get("eventId")
        for m in ev.get("moments") or []:
            period, _utc, g, s = m[0], m[1], m[2], m[3]
            if g is None:
                continue
            n_moments_raw += 1
            for t, p, x, y, z in m[5]:
                per.append(period); gc.append(g); sc.append(s); tid.append(t); pid.append(p); xs.append(x); ys.append(y); zs.append(z); evid.append(eid)
    df = pd.DataFrame({"period": per, "game_clock": gc, "shot_clock": sc, "team_id": tid, "player_id": pid, "x": xs, "y": ys, "z": zs, "event_id": evid})
    raw_rows = len(df)
    df = df.drop_duplicates(subset=["period", "game_clock", "player_id"], keep="first")
    n_unique_moments = int(df[["period", "game_clock"]].drop_duplicates().shape[0])
    inv = {"n_event_containers": n_containers, "n_raw_moments": n_moments_raw, "n_raw_rows": raw_rows, "n_dedup_rows": int(len(df)),
           "n_unique_moments": n_unique_moments, "duplication_factor_moments": round(n_moments_raw / max(n_unique_moments, 1), 3),
           "periods": sorted(int(p) for p in df.period.unique())}
    return df, inv


def possession_frames(df: pd.DataFrame) -> pd.DataFrame:
    ball = df[df.player_id == BALL_ID].drop_duplicates(subset=["period", "game_clock"], keep="first")[["period", "game_clock", "x", "y", "z"]].rename(columns={"x": "bx", "y": "by", "z": "bz"})
    pl_ = df[df.player_id != BALL_ID].merge(ball, on=["period", "game_clock"], how="inner")
    pl_["ball_dist"] = np.sqrt((pl_.x - pl_.bx) ** 2 + (pl_.y - pl_.by) ** 2)
    pl_ = pl_[pl_.bz <= POSSESSION_MAX_BALL_Z].sort_values("ball_dist")
    near = pl_.groupby(["period", "game_clock"], as_index=False).first()
    near = near[near.ball_dist <= POSSESSION_MAX_DIST][["period", "game_clock", "team_id"]].rename(columns={"team_id": "off_team_id"})
    return near.sort_values(["period", "game_clock"], ascending=[True, False]).reset_index(drop=True)


class Labeler:
    """Vectorised window_label with source semantics: majority team in [clock+lead, clock+lead+2.0], >= 5 frames."""
    def __init__(self, poss: pd.DataFrame):
        self.byp = {}
        for p, g in poss.groupby("period"):
            g = g.sort_values("game_clock")
            self.byp[int(p)] = (g.game_clock.values, g.off_team_id.values)

    def label(self, period: int, clock: float, lead: float) -> int | None:
        if period not in self.byp:
            return None
        c, t = self.byp[period]
        lo, hi = tracking_clock_target(clock, lead), tracking_clock_target(clock, lead) + LOOKBACK_S
        i0, i1 = np.searchsorted(c, lo, "left"), np.searchsorted(c, hi, "right")
        if i1 - i0 < MIN_FRAMES:
            return None
        teams, counts = np.unique(t[i0:i1], return_counts=True)
        # source: sort by n descending and take first -> ties resolve by polars' stable order (team order of first appearance);
        # we take the max count; on an exact tie prefer the team appearing first in the window (same as stable sort of group_by output order)
        best = counts.max(); cands = teams[counts == best]
        if len(cands) == 1:
            return int(cands[0])
        first_seen = {}
        for x in t[i0:i1]:
            first_seen.setdefault(int(x), len(first_seen))
        return int(min(cands, key=lambda x: first_seen[int(x)]))


def agreement(lab: Labeler, events: pd.DataFrame, lead: float) -> tuple[int, int]:
    n = agree = 0
    for ev in events.itertuples():
        l = lab.label(int(ev.period), float(ev.secs_left), lead)
        if l is None:
            continue
        n += 1; agree += int(l == int(ev.team_id))
    return agree, n


def calibrate(lab: Labeler, shots: pd.DataFrame) -> tuple[float, float, list]:
    best_lead, best_rate, curve = LEAD_GRID[0], -1.0, []
    for lead in LEAD_GRID:
        a, n = agreement(lab, shots, lead); rate = a / n if n else 0.0
        curve.append({"lead": lead, "agree": a, "n": n, "rate": rate})
        if rate > best_rate:
            best_lead, best_rate = lead, rate
    return best_lead, best_rate, curve


def load_pbp(pbp: pd.DataFrame) -> pd.DataFrame:
    d = pbp.copy()
    d["secs_left"] = d.clock.map(parse_clock); d["period"] = d.period.astype(int); d["team_id"] = pd.to_numeric(d.teamId, errors="coerce").fillna(0).astype(int)
    d["is_fga"] = d.isFieldGoal.astype(str) == "1"; d["is_turnover"] = d.actionType == "Turnover"
    return d[d.secs_left.notna()]


def run_game(json_path: Path, pbp: pd.DataFrame, out_dir: Path, source_lead: float | None = None) -> dict:
    gid, events, g = load_game_json(json_path)
    df, inv = frames_from_events(events)
    poss = possession_frames(df); lab = Labeler(poss)
    p = load_pbp(pbp[pbp.gameId.astype(str).str.zfill(10) == gid] if "gameId" in pbp.columns else pbp)
    shots = p[p.is_fga & (p.team_id != 0)]; tos = p[p.is_turnover & (p.team_id != 0)]
    lead, rate, curve = calibrate(lab, shots)
    a0, n0 = agreement(lab, shots, 0.0); ta0, tn0 = agreement(lab, tos, 0.0); ta, tn = agreement(lab, tos, lead)
    ties = [c["lead"] for c in curve if c["n"] and abs(c["rate"] - rate) < 1e-12]
    halves = {}
    for name, pers in (("H1", (1, 2)), ("H2", (3, 4))):
        sh = shots[shots.period.isin(pers)]; th = tos[tos.period.isin(pers)]
        if len(sh) >= 20:
            l_h, r_h, _ = calibrate(lab, sh); ta_h, tn_h = agreement(lab, th, l_h); ta_g, tn_g = agreement(lab, th, lead)
            halves[name] = {"lead": l_h, "shot_rate": r_h, "n_shots": int(len(sh)), "to_agree_half_lead": ta_h, "to_agree_game_lead": ta_g, "n_to": tn_h}
    # eventId / container diagnostic
    cont = {}
    for ev in events:
        try:
            eid = int(ev.get("eventId"))
        except Exception:
            continue
        ms = [m for m in (ev.get("moments") or []) if m[2] is not None]
        if ms:
            cont[eid] = (int(ms[0][0]), max(m[2] for m in ms), min(m[2] for m in ms))
    def ev_diag(evs):
        matched = inside = 0
        for e in evs.itertuples():
            c = cont.get(int(e.actionNumber))
            if c is None or c[0] != int(e.period):
                continue
            matched += 1
            lo, hi = tracking_clock_target(e.secs_left, lead), tracking_clock_target(e.secs_left, lead) + LOOKBACK_S
            inside += int(c[2] <= hi and c[1] >= lo)
        return {"n": int(len(evs)), "eventid_matched": matched, "container_overlaps_calibrated_window": inside}
    res = {"game_id": gid, "file": json_path.name, "inventory": inv, "n_pbp_rows": int(len(p)),
           "n_calibration_shots": int(n0), "n_holdout_turnovers": int(tn0),
           "naive_shot_agree": int(a0), "naive_shot_rate": a0 / n0 if n0 else None,
           "calibrated_lead_s": lead, "calibrated_shot_rate": rate,
           "calibrated_shot_agree": next(c["agree"] for c in curve if c["lead"] == lead), "calibrated_shot_n": next(c["n"] for c in curve if c["lead"] == lead),
           "naive_to_rate": ta0 / tn0 if tn0 else None, "calibrated_to_agree": int(ta), "calibrated_to_n": int(tn), "calibrated_to_rate": ta / tn if tn else None,
           "tie_leads": ties, "tie_status": "UNIQUE" if len(ties) == 1 else f"TIE_{len(ties)}_SMALLEST_CHOSEN",
           "quality_status": ("NO_TRACKING_MOMENTS" if inv["n_raw_moments"] == 0 else "INSUFFICIENT_CALIBRATION_EVENTS" if n0 < 20 else "INSUFFICIENT_HOLDOUT_EVENTS" if tn0 < 5 else "CALIBRATED"),
           "curve": curve, "halves": halves, "eventid_diag": {"shots": ev_diag(shots), "turnovers": ev_diag(tos)},
           "source_reported_lead": source_lead}
    (out_dir / "games").mkdir(parents=True, exist_ok=True)
    (out_dir / "games" / f"{gid}.json").write_text(json.dumps(res, indent=1))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-dir", default=str(RAW / "sportvu" / "json"))
    ap.add_argument("--pbp", default=str(RAW / "pbp" / "2015-16" / "all.parquet"))
    ap.add_argument("--games", default="", help="comma-separated file stems to restrict to (e.g. the external 10)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    test_sign_convention()
    if a.self_test:
        print("sign-convention test PASSED"); return 0
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    pbp = pd.read_parquet(a.pbp)
    files = sorted(glob.glob(os.path.join(a.json_dir, "*.json")))
    if a.games:
        want = set(a.games.split(",")); files = [f for f in files if Path(f).stem in want]
    done = {p.stem for p in (out / "games").glob("*.json")} if a.resume else set()
    for i, f in enumerate(files, 1):
        stem = Path(f).stem
        try:
            gid = json.loads(Path(f).read_text()[:200].split('"events"')[0] + '"events":[]}')["gameid"]
        except Exception:
            gid = None
        if gid and gid in done:
            continue
        try:
            r = run_game(Path(f), pbp, out)
            print(f"[{i}/{len(files)}] {stem} lead {r['calibrated_lead_s']} shots {r['naive_shot_rate']}->{r['calibrated_shot_rate']} TO {r['naive_to_rate']}->{r['calibrated_to_rate']} {r['quality_status']}", flush=True)
        except Exception as e:  # noqa: BLE001
            (out / "games").mkdir(parents=True, exist_ok=True)
            (out / "games" / f"FAILED_{stem}.json").write_text(json.dumps({"file": stem, "error": repr(e)}))
            print(f"[{i}/{len(files)}] {stem} FAILED {e!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
