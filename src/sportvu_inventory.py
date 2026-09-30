#!/usr/bin/env python3
"""local SportVU inventory and de-duplication census.

Per raw SportVU JSON file: parseable?, event containers, raw moments, unique (period, utc_ms) moments
[true duplicates removed], unique (period, game_clock) moments [what the latency method and Screen
game_frames() collapse to], moments with exactly 11 entities, periods; the v2 npz layer's frame count
and stored-possession count for the same game; and membership in each analysis universe.

Writes audit/SPORTVU_GAME_INVENTORY.csv (one row per raw file; resumable) — the .md summary is written
by the caller after the pass completes.  No outcome quantity is read or written.
"""
from __future__ import annotations
import argparse, csv, glob, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]
JSON_DIR = os.environ.get("SPORTVU_JSON_DIR", "data/external/sportvu/json")
NPZ_DIR = os.environ.get("NPZ_DIR", "data/derived/possessions")
PBP = os.environ.get("PBP_PARQUET", "data/external/pbp/2015-16/all.parquet")
P075 = os.environ.get("V3_DIR", "data/derived/phase0_75")
SCREEN = Path(os.environ.get("SCREEN_PROJECT_DIR", "data/derived/screen")) / "data"
EXTERNAL_10 = ["0021500490", "0021500491", "0021500492", "0021500493", "0021500494",
               "0021500495", "0021500498", "0021500502", "0021500503", "0021500504"]
FIELDS = ["stem", "game_id", "raw_file_exists", "raw_file_parseable", "n_event_containers", "n_containers_with_moments",
          "n_raw_moments", "n_unique_period_utc", "n_unique_period_clock", "n_moments_11_entities",
          "duplication_factor_utc", "clock_collapse_factor", "periods", "npz_exists", "npz_n_possessions", "npz_n_frames",
          "npz_frames_over_unique_utc", "pbp_v3_available", "pbp_rows", "v3_covered", "v3_n_possessions", "n_frame_links",
          "screen_used", "timeout_tracking_universe", "timeout_analysis_game", "external_10_overlap", "reason"]


def inventory_json(path: str) -> dict:
    try:
        g = json.load(open(path))
    except Exception as e:  # noqa: BLE001
        return {"raw_file_parseable": False, "reason": f"json_parse_error:{type(e).__name__}"}
    evs = g.get("events") or []
    utc, clk, n_raw, n11, nwm, periods = set(), set(), 0, 0, 0, set()
    for ev in evs:
        ms = ev.get("moments") or []
        if ms:
            nwm += 1
        for m in ms:
            n_raw += 1
            p, t, c = m[0], m[1], m[2]
            if p is None or t is None:
                continue
            periods.add(int(p)); utc.add((int(p), int(t)))
            if c is not None:
                clk.add((int(p), float(c)))
            if len(m[5]) == 11:
                n11 += 1
    return {"game_id": str(g.get("gameid")), "raw_file_parseable": True, "n_event_containers": len(evs), "n_containers_with_moments": nwm,
            "n_raw_moments": n_raw, "n_unique_period_utc": len(utc), "n_unique_period_clock": len(clk), "n_moments_11_entities": n11,
            "duplication_factor_utc": round(n_raw / max(len(utc), 1), 3), "clock_collapse_factor": round(len(utc) / max(len(clk), 1), 3),
            "periods": "|".join(str(p) for p in sorted(periods)), "reason": ""}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(R / "audit" / "SPORTVU_GAME_INVENTORY.csv")); ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    pbp = pd.read_parquet(PBP, columns=["gameId"]); pbp_counts = pbp.gameId.astype(str).value_counts().to_dict()
    v3 = pd.read_parquet(f"{P075}/possessions_v3.parquet", columns=["game_id"]); v3_counts = v3.game_id.astype(str).value_counts().to_dict()
    links = pd.read_parquet(f"{P075}/possessions_v3_sportvu_frame_links.parquet", columns=["game_id"]); link_counts = links.game_id.astype(str).value_counts().to_dict()
    screen_games = set(pd.read_parquet(SCREEN / "screens_v3.parquet", columns=["game_id"]).game_id.astype(str))
    pfv = pd.read_parquet(os.environ.get("TIMEOUT_PFV_PARQUET", "data/derived/v3_movement_pfv.parquet"), columns=["game_id", "sportvu_link_valid"])
    tracking_games = set(pfv[pfv.sportvu_link_valid].game_id.astype(str))
    panel = pd.read_parquet(R / "data" / "analysis_panel.parquet", columns=["game_id", "has_valid_offensive_TSS", "has_valid_defensive_TSS"])
    analysis_games = set(panel[panel.has_valid_offensive_TSS | panel.has_valid_defensive_TSS].game_id.astype(str))
    done = set()
    if a.resume and os.path.exists(a.out):
        done = set(pd.read_csv(a.out, dtype=str).stem)
    mode = "a" if done else "w"
    with open(a.out, mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if mode == "w":
            w.writeheader()
        for path in sorted(glob.glob(f"{JSON_DIR}/*.json")):
            stem = Path(path).stem
            if stem in done:
                continue
            row = {k: "" for k in FIELDS}; row.update(stem=stem, raw_file_exists=True); row.update(inventory_json(path))
            gid = row.get("game_id", "")
            npz_path = f"{NPZ_DIR}/{stem}.npz"; row["npz_exists"] = os.path.exists(npz_path)
            if row["npz_exists"]:
                d = np.load(npz_path, allow_pickle=True)
                row["npz_n_possessions"] = int(d["n"]) if "n" in d.files else 0
                row["npz_n_frames"] = int(d["game_clock"].shape[0]) if "game_clock" in d.files else 0
                if "game_clock" not in d.files:
                    row["reason"] = "NPZ_EMPTY_OR_MALFORMED:" + "|".join(d.files)
                if row.get("n_unique_period_utc"):
                    row["npz_frames_over_unique_utc"] = round(row["npz_n_frames"] / max(row["n_unique_period_utc"], 1), 3)
                if not gid or gid == "None":
                    gid = str(d["game_id"]); row["game_id"] = gid
            row["pbp_rows"] = pbp_counts.get(gid, 0); row["pbp_v3_available"] = row["pbp_rows"] > 0
            row["v3_n_possessions"] = v3_counts.get(gid, 0); row["v3_covered"] = row["v3_n_possessions"] > 0
            row["n_frame_links"] = link_counts.get(gid, 0)
            row["screen_used"] = gid in screen_games; row["timeout_tracking_universe"] = gid in tracking_games
            row["timeout_analysis_game"] = gid in analysis_games; row["external_10_overlap"] = gid in EXTERNAL_10
            if not row["reason"]:
                row["reason"] = ("OK" if row["v3_covered"] and row["n_frame_links"] else "NO_PBP_V3" if not row["pbp_v3_available"]
                                 else "NO_V3_POSSESSIONS" if not row["v3_covered"] else "NO_FRAME_LINKS" if not row["n_frame_links"] else "OK")
            w.writerow(row); fh.flush()
            print(stem, gid, row["reason"], flush=True)
    print("INVENTORY_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
