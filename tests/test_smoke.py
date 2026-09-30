#!/usr/bin/env python3
"""Level-1 reproduction: regenerate both figures from the shipped aggregates and assert every headline number.
Runs without any external data.   python3 tests/test_smoke.py
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "_out"


def close(a, b, tol):
    assert abs(a - b) <= tol, f"{a} vs {b} (tol {tol})"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ALIGNMENT_EFG_TABLE=str(ROOT / "results" / "external_artifact_generalization.csv"), ALIGNMENT_FIGURE_DIR=str(OUT))
    subprocess.run([sys.executable, str(ROOT / "src" / "figures_final.py")], check=True, env=env, stdout=subprocess.DEVNULL)
    for f in ("FIG1_naive_vs_corrected_spacing_efg.pdf", "FIG1_naive_vs_corrected_spacing_efg.png", "FIG2_measurement_resource_evidence.pdf", "FIG2_measurement_resource_evidence.png"):
        assert (OUT / f).exists(), f
    # the regenerated PNGs must match the released ones byte for byte (PDFs carry a render timestamp, so they are not compared)
    for stem in ("FIG1_naive_vs_corrected_spacing_efg", "FIG2_measurement_resource_evidence"):
        a = hashlib.sha256((OUT / f"{stem}.png").read_bytes()).hexdigest()
        b = hashlib.sha256((ROOT / "figures" / f"{stem}.png").read_bytes()).hexdigest()
        assert a == b, f"{stem}.png regenerated {a[:16]} != released {b[:16]}"
    # held-out validation
    S = json.load(open(ROOT / "results" / "global_shift_summary.json"))["universe"]["all_calibratable"]
    close(S["M0"]["pooled"], 0.393, 0.0005); close(S["M1"]["pooled"], 0.942, 0.0005); close(S["M2"]["pooled"], 0.932, 0.0005)
    assert S["M0"]["n_events"] == 16943 and S["M0"]["n_games"] == 631
    # wrong-state attribution
    close(S["M0"]["shot_wrong_team_rate"], 0.690, 0.0005); close(S["M1"]["shot_wrong_team_rate"], 0.035, 0.0005)
    SC = json.load(open(ROOT / "results" / "global_shift_screens.json"))
    assert SC["n_screens"] == 7625; close(SC["M0"]["frac_onset_lt_0.5s"], 0.277, 0.0005); close(SC["M1"]["frac_onset_lt_0.5s"], 0.047, 0.0005); close(SC["M1"]["reassigned_vs_M0"], 0.230, 0.0005)
    # temporal x semantic speed cancellation
    T = json.load(open(ROOT / "results" / "temporal_semantic_2x2.json"))["metrics"]["M1"]
    close(T["std_diff_A_minus_C_over_sdD"], 0.22, 0.005); close(T["std_diff_A_minus_B_over_sdD"], -0.20, 0.005); close(T["std_diff_A_minus_D_over_sdD"], 0.03, 0.005)
    # eFG artefact
    E = pd.read_csv(ROOT / "results" / "external_artifact_generalization.csv")
    nv = E[E.axis == "naive"].sort_values("quartile").efg.values; cl = E[E.axis == "calibrated"].sort_values("quartile").efg.values
    close(nv[0], 0.478, 0.0005); close(nv[3], 0.572, 0.0005)
    for v, ref in zip(cl, (0.524, 0.498, 0.491, 0.505)):
        close(v, ref, 0.0005)
    assert int(E[E.axis == "naive"].n.sum()) == 27563 and int(E[E.axis == "calibrated"].n.sum()) == 64764
    # supporting matched-shot check (not the primary figure): the shots common to both alignments
    MS = json.load(open(ROOT / "results" / "matched_shot_audit.json"))
    assert MS["intersection_n"] == 26177
    for v, ref in zip(MS["common_naive"]["efg"], (0.485, 0.532, 0.547, 0.577)):
        close(v, ref, 0.0005)
    for v, ref in zip(MS["common_corrected"]["efg"], (0.546, 0.515, 0.530, 0.549)):
        close(v, ref, 0.0005)
    close(MS["common_naive"]["q4_minus_q1"], 0.092, 0.0005); close(MS["common_corrected"]["q4_minus_q1"], 0.003, 0.0005)
    assert MS["common_naive"]["monotone_nondecreasing"] and not MS["common_corrected"]["monotone_nondecreasing"]
    # taxonomy shares
    X = pd.read_csv(ROOT / "results" / "taxonomy_summary.csv").set_index("class")
    close(X.loc["MULTIMODAL", "fraction"], 0.190, 0.0005); close(X.loc["DRIFTING", "fraction"], 0.106, 0.0005)
    # live-play prevalence
    P = json.load(open(ROOT / "results" / "prevalence_summary.json"))
    share = P.get("corpus_nonlive_frame_share", P.get("nonlive_frame_share"))
    assert share is not None and abs(share - 0.147) <= 0.0005, share
    # shipped per-game table integrity
    A = pd.read_csv(ROOT / "results" / "clock_alignment_v1.csv", dtype={"game_id": str}); assert len(A) == 632
    print("SMOKE TEST PASSED: figures regenerated in tests/_out/; all headline numbers match the shipped aggregates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
