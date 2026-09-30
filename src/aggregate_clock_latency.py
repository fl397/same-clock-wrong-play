#!/usr/bin/env python3
"""Aggregate per-game clock-latency calibrations into the all-game table.

Rules below are FROZEN before the full pass is read (written 2026-09-19 while the pass was at 467/632 games;
only the 10 external games and their replication had been inspected). They use ONLY independent alignment
labels (shot-team agreement for calibration, turnover-team agreement held out). No TSS/RSE/outcome is read.

Per-game flags
  quality_status        from the producer: CALIBRATED | INSUFFICIENT_CALIBRATION_EVENTS (<20 labelled shots)
                        | INSUFFICIENT_HOLDOUT_EVENTS (<5 turnovers)
  bimodal_curve         top-2 leads of the shot-agreement curve >= 1.0 s apart AND rate difference <= 1/n (within one event)
  holdout_status        HOLDOUT_PASS if calibrated turnover agreement >= 0.80, else HOLDOUT_FAIL
  drift_status          ADEQUATE if |lead_H1 - lead_H2| <= 2.0 s (the label-window length; the source's own tolerance
                        argument) ; MATERIALLY_DRIFTING if > 2.0 s ; UNASSESSED if either half has < 20 labelled shots
  lead_status           CLOCK_CALIBRATION_VALIDATED  iff quality_status == CALIBRATED and HOLDOUT_PASS and not bimodal
                        and drift_status != MATERIALLY_DRIFTING
                        AMBIGUOUS_LEAD               iff bimodal (and otherwise CALIBRATED)
                        DRIFTING_LEAD                iff MATERIALLY_DRIFTING
                        HOLDOUT_FAIL / INSUFFICIENT_* otherwise
Global gate (both required)
  CLEAR_NONZERO_LEAD          median validated lead >= 1.0 s AND >= 90 % of validated games have lead >= 1.0 s
  SUBSTANTIAL_HOLDOUT_GAIN    pooled held-out turnover agreement (validated games) improves by >= 20 percentage points
                              from lead 0 to the calibrated lead
Insufficient / non-validated games: reported; NO global fallback lead is applied here (that treatment is
specified separately, not in this aggregator).
"""
from __future__ import annotations
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]
IN = R / "audit" / "latency_all_games" / "games"
OUT_CSV = R / "audit" / "PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.csv"
OUT_MD = R / "audit" / "PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.md"
EXTERNAL_10 = {"0021500490", "0021500491", "0021500492", "0021500493", "0021500494", "0021500495", "0021500498", "0021500502", "0021500503", "0021500504"}


def row_from(d: dict) -> dict:
    curve = sorted(d["curve"], key=lambda c: (-c["rate"], c["lead"]))
    lead = d["calibrated_lead_s"]; at = next(c for c in d["curve"] if c["lead"] == lead) if d["curve"] else {"agree": 0, "n": 0, "rate": None}
    top2 = curve[:2]; n_at = max(at["n"], 1)
    if not curve: top2 = []
    bimodal = len(top2) == 2 and abs(top2[0]["lead"] - top2[1]["lead"]) >= 1.0 and (top2[0]["rate"] - top2[1]["rate"]) <= 1.0 / n_at
    h = d.get("halves") or {}
    h1, h2 = h.get("H1"), h.get("H2")
    if h1 and h2 and h1["n_shots"] >= 20 and h2["n_shots"] >= 20:
        dl = abs(h1["lead"] - h2["lead"]); drift = "ADEQUATE" if dl <= 2.0 else "MATERIALLY_DRIFTING"
    else:
        dl, drift = np.nan, "UNASSESSED"
    to_rate = d.get("calibrated_to_rate"); q = d["quality_status"]
    holdout = ("HOLDOUT_PASS" if (to_rate is not None and to_rate >= 0.80) else "HOLDOUT_FAIL") if q == "CALIBRATED" else "NOT_ASSESSED"
    if q != "CALIBRATED":
        status = q
    elif holdout == "HOLDOUT_FAIL":
        status = "HOLDOUT_FAIL"
    elif bimodal:
        status = "AMBIGUOUS_LEAD"
    elif drift == "MATERIALLY_DRIFTING":
        status = "DRIFTING_LEAD"
    else:
        status = "CLOCK_CALIBRATION_VALIDATED"
    ev = d["eventid_diag"]; inv = d["inventory"]
    return {"game_id": d["game_id"], "file": d["file"], "external_10": d["game_id"] in EXTERNAL_10, "source_reported_lead": d.get("source_reported_lead"),
            "n_event_containers": inv["n_event_containers"], "n_raw_moments": inv["n_raw_moments"], "n_unique_period_clock": inv["n_unique_moments"],
            "periods": "|".join(map(str, inv["periods"])), "n_pbp_rows": d["n_pbp_rows"],
            "calibrated_lead_s": lead, "tie_status": d["tie_status"], "tie_leads": "|".join(map(str, d["tie_leads"])),
            "shot_agree_calibrated": at["agree"], "shot_n_calibrated": at["n"], "shot_rate_calibrated": at["rate"],
            "shot_n_naive": d["n_calibration_shots"], "shot_rate_naive": d["naive_shot_rate"],
            "to_agree_calibrated": d["calibrated_to_agree"], "to_n_calibrated": d["calibrated_to_n"], "to_rate_calibrated": to_rate,
            "to_n_naive": d["n_holdout_turnovers"], "to_rate_naive": d["naive_to_rate"],
            "second_peak_lead": top2[1]["lead"] if len(top2) > 1 else None, "second_peak_rate": top2[1]["rate"] if len(top2) > 1 else None, "bimodal_curve": bimodal,
            "lead_H1": h1["lead"] if h1 else None, "shot_n_H1": h1["n_shots"] if h1 else None, "shot_rate_H1_at_H1_lead": h1["shot_rate"] if h1 else None,
            "lead_H2": h2["lead"] if h2 else None, "shot_n_H2": h2["n_shots"] if h2 else None, "shot_rate_H2_at_H2_lead": h2["shot_rate"] if h2 else None,
            "abs_half_lead_diff_s": dl, "drift_status": drift,
            "to_H1_agree_game_lead": h1["to_agree_game_lead"] if h1 else None, "to_H1_agree_half_lead": h1["to_agree_half_lead"] if h1 else None, "to_H1_n": h1["n_to"] if h1 else None,
            "to_H2_agree_game_lead": h2["to_agree_game_lead"] if h2 else None, "to_H2_agree_half_lead": h2["to_agree_half_lead"] if h2 else None, "to_H2_n": h2["n_to"] if h2 else None,
            "eventid_shots_n": ev["shots"]["n"], "eventid_shots_matched": ev["shots"]["eventid_matched"], "eventid_shots_container_overlaps_window": ev["shots"]["container_overlaps_calibrated_window"],
            "eventid_to_n": ev["turnovers"]["n"], "eventid_to_matched": ev["turnovers"]["eventid_matched"], "eventid_to_container_overlaps_window": ev["turnovers"]["container_overlaps_calibrated_window"],
            "quality_status": q, "holdout_status": holdout, "lead_status": status}


def main() -> int:
    files = sorted(f for f in glob.glob(str(IN / "*.json")) if not Path(f).name.startswith("FAILED_"))
    failed = sorted(Path(f).name for f in glob.glob(str(IN / "FAILED_*.json")))
    assert not failed, f"unprocessed games: {failed}"
    df = pd.DataFrame([row_from(json.load(open(f))) for f in files]).sort_values("game_id")
    df.to_csv(OUT_CSV, index=False)
    v = df[df.lead_status == "CLOCK_CALIBRATION_VALIDATED"]; cal = df[df.quality_status == "CALIBRATED"]
    def pooled(x, a, n): return (x[a].sum(), x[n].sum(), x[a].sum() / max(x[n].sum(), 1))
    ps = pooled(cal, "shot_agree_calibrated", "shot_n_calibrated"); pt = pooled(cal, "to_agree_calibrated", "to_n_calibrated")
    naive_s = (cal.shot_rate_naive * cal.shot_n_naive).sum() / max(cal.shot_n_naive.sum(), 1); naive_t = (cal.to_rate_naive * cal.to_n_naive).sum() / max(cal.to_n_naive.sum(), 1)
    vt = pooled(v, "to_agree_calibrated", "to_n_calibrated"); v_naive_t = (v.to_rate_naive * v.to_n_naive).sum() / max(v.to_n_naive.sum(), 1)
    med = float(v.calibrated_lead_s.median()) if len(v) else float("nan"); frac_ge1 = float((v.calibrated_lead_s >= 1.0).mean()) if len(v) else float("nan")
    clear = bool(len(v) and med >= 1.0 and frac_ge1 >= 0.90); gain = vt[2] - v_naive_t; substantial = bool(len(v) and gain >= 0.20)
    q = v.calibrated_lead_s.quantile([0, .05, .25, .5, .75, .95, 1]).round(2).to_dict() if len(v) else {}
    summary = {"n_games": int(len(df)), "n_calibrated": int(len(cal)), "lead_status_counts": df.lead_status.value_counts().to_dict(), "drift_status_counts": df.drift_status.value_counts().to_dict(),
               "holdout_status_counts": df.holdout_status.value_counts().to_dict(), "bimodal_n": int(df.bimodal_curve.sum()), "tie_n": int((df.tie_status != "UNIQUE").sum()),
               "validated_lead_quantiles": q, "validated_lead_mean": float(v.calibrated_lead_s.mean()) if len(v) else None, "validated_lead_sd": float(v.calibrated_lead_s.std()) if len(v) else None,
               "validated_lead_histogram": v.calibrated_lead_s.value_counts().sort_index().to_dict(),
               "pooled_shot_calibrated_all_calibrated_games": ps, "pooled_shot_naive": naive_s, "pooled_to_calibrated_all_calibrated_games": pt, "pooled_to_naive": naive_t,
               "validated_games_pooled_to_calibrated": vt, "validated_games_pooled_to_naive": v_naive_t, "held_out_gain_pp": gain,
               "eventid_shots_matched_frac": float(df.eventid_shots_matched.sum() / max(df.eventid_shots_n.sum(), 1)),
               "eventid_shots_container_overlap_frac_of_matched": float(df.eventid_shots_container_overlaps_window.sum() / max(df.eventid_shots_matched.sum(), 1)),
               "eventid_to_matched_frac": float(df.eventid_to_matched.sum() / max(df.eventid_to_n.sum(), 1)),
               "eventid_to_container_overlap_frac_of_matched": float(df.eventid_to_container_overlaps_window.sum() / max(df.eventid_to_matched.sum(), 1)),
               "gate_CLEAR_NONZERO_LEAD": clear, "gate_SUBSTANTIAL_HOLDOUT_GAIN": substantial, "median_validated_lead": med, "frac_validated_lead_ge_1s": frac_ge1}
    (R / "audit" / "clock_latency_all_games_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    ext = df[df.external_10]
    md = ["# PBP-to-SportVU clock latency, all local SportVU games", "",
          f"Producer: `src/clock_latency_calibration.py` (per-game JSON in `audit/latency_all_games/games/`, {len(df)} games) → `src/aggregate_clock_latency.py` (rules frozen in its docstring before the pass was read). Table: `PBP_SPORTVU_CLOCK_LATENCY_ALL_GAMES.csv`. Calibration labels: shot-team agreement only; held-out: turnover-team agreement. No outcome quantity read.", "",
          "## Per-game calibration — status counts", "", "| lead_status | games |", "|---|---|"] + [f"| {k} | {n} |" for k, n in summary["lead_status_counts"].items()] + [
          "", f"Ties (smallest lead chosen): {summary['tie_n']} games. Bimodal curves: {summary['bimodal_n']} games.", "",
          "## Global lead distribution (CLOCK_CALIBRATION_VALIDATED games only)", "",
          f"n = {len(v)}; mean = {summary['validated_lead_mean']:.2f} s; sd = {summary['validated_lead_sd']:.2f} s; quantiles (min/5/25/50/75/95/max) = " + " / ".join(f"{q[k]:.1f}" for k in sorted(q)) + " s.", "",
          "| lead (s) | validated games |", "|---|---|"] + [f"| {k:.1f} | {n} |" for k, n in summary["validated_lead_histogram"].items()] + [
          "", "## Held-out turnover validation", "", "| population | naive (lead 0) | calibrated |", "|---|---|---|",
          f"| all CALIBRATED games, shots (calibration metric) | {naive_s:.4f} | {ps[0]}/{ps[1]} = {ps[2]:.4f} |",
          f"| all CALIBRATED games, turnovers (held out) | {naive_t:.4f} | {pt[0]}/{pt[1]} = {pt[2]:.4f} |",
          f"| VALIDATED games, turnovers (held out) | {v_naive_t:.4f} | {vt[0]}/{vt[1]} = {vt[2]:.4f} (gain {gain*100:+.1f} pp) |", "",
          "Held-out status: " + ", ".join(f"{k} {n}" for k, n in summary["holdout_status_counts"].items()) + ".", "",
          "## Half-game drift sensitivity", "", "Rule: |lead_H1 − lead_H2| ≤ 2.0 s (label-window length) → ADEQUATE; > 2.0 s → MATERIALLY_DRIFTING; either half < 20 labelled shots → UNASSESSED.", "",
          "| drift_status | games |", "|---|---|"] + [f"| {k} | {n} |" for k, n in summary["drift_status_counts"].items()] + [
          "", f"Distribution of |ΔH| among assessed games: " + ", ".join(f"{k:.1f}s: {n}" for k, n in df.abs_half_lead_diff_s.dropna().value_counts().sort_index().items()) + ".", "",
          "## SportVU eventId / container diagnostic", "",
          f"PBP `actionNumber` matches a SportVU event container id (same period) for {summary['eventid_shots_matched_frac']*100:.1f} % of shots and {summary['eventid_to_matched_frac']*100:.1f} % of turnovers; of the matched containers, {summary['eventid_shots_container_overlap_frac_of_matched']*100:.1f} % (shots) / {summary['eventid_to_container_overlap_frac_of_matched']*100:.1f} % (turnovers) have a clock span overlapping the calibrated label window. Reading: containers are keyed to PBP actions, but their clock spans are not a substitute for calibration (they overlap by construction only when the container is wide enough to absorb the lead); no Timeout/Screen producer uses eventId for alignment.", "",
          "## External 10-game overlap (reference)", "", "| game_id | source lead | our lead | status |", "|---|---|---|---|"] + [f"| {r.game_id} | {r.source_reported_lead} | {r.calibrated_lead_s} | {r.lead_status} |" for r in ext.itertuples()] + [
          "", "## Global gate (rules fixed in the aggregator docstring)", "",
          f"- CLEAR_NONZERO_LEAD: median validated lead {med:.2f} s ≥ 1.0 and {frac_ge1*100:.1f} % of validated games ≥ 1.0 s → **{'PASS' if clear else 'FAIL'}**",
          f"- SUBSTANTIAL_HOLDOUT_GAIN: held-out turnover agreement {v_naive_t:.4f} → {vt[2]:.4f} ({gain*100:+.1f} pp, threshold +20 pp) → **{'PASS' if substantial else 'FAIL'}**",
          f"- Combined: **{'GATE_PASS' if clear and substantial else 'GATE_FAIL'}** (the third condition — TSS windows are timing-dependent — is established by the companion timeout-window study).", "",
          "Non-validated games carry no lead into any downstream rebuild; their treatment (exclusion vs. global fallback) is specified separately, before any rerun."]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps({k: v_ for k, v_ in summary.items() if k not in ("validated_lead_histogram",)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
