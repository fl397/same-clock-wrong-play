#!/usr/bin/env python3
"""The two figures, rendered only from the shipped aggregate results.

FIGURE 1  figures/FIG1_naive_vs_corrected_spacing_efg.{pdf,png}
    eFG% by offensive-spacing quartile under the naive equal-clock join vs the corrected join, on the full eligible
    sample of each join (grouped bars; presentation-only choices, the eFG values are unchanged).
    Source: results/external_artifact_generalization.csv; the matched-sample supporting check on the shots eligible
    under BOTH alignments is in results/matched_shot_audit.json and docs/validation/MATCHED_SHOT_VALIDATION.md.
    Phenomenon and the 10-game example: ismayc/tracking-study; season-scale generalization: this work.
FIGURE 2  figures/FIG2_measurement_resource_evidence.{pdf,png}
    (A) per-game held-out turnover-team agreement, naive vs fixed +4 s vs game-specific calibration
        (results/global_shift_by_game.csv, results/global_shift_summary.json);
    (B) wrong-state attribution before/after the +4 s shift (results/global_shift_summary.json, results/global_shift_screens.json);
    (C) mean offensive-player speed in the four temporal x semantic cells (results/temporal_semantic_2x2.json).
No tracking data are read; nothing is recomputed.  Captions: docs/validation/FIGURE_VALUES.md and figures/*.caption.txt.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = Path(__file__).resolve().parents[1]
# The eFG comparison table lives in the clock-alignment analysis; ALIGNMENT_EFG_TABLE overrides for a self-contained repository copy.
EFG_TABLE = Path(os.environ.get("ALIGNMENT_EFG_TABLE", R / "results" / "external_artifact_generalization.csv"))
OUT = Path(os.environ.get("ALIGNMENT_FIGURE_DIR", R / "figures" / "final"))
NAIVE, SHIFT, PERGAME, LIVE = "#8A8A8A", "#C9622B", "#2E6F9E", "#6A994E"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5})


def save(fig, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig1() -> dict:
    E = pd.read_csv(EFG_TABLE)
    nv = E[E.axis == "naive"].sort_values("quartile"); cl = E[E.axis == "calibrated"].sort_values("quartile")
    fig, ax = plt.subplots(figsize=(6.2, 4.2)); x = np.arange(4); w = 0.38
    a = ax
    a.bar(x - w / 2, 100 * nv.efg, w, color=NAIVE, label=f"naive equal-clock join ({int(nv.n.sum()):,} shots)")
    a.bar(x + w / 2, 100 * cl.efg, w, color=PERGAME, label=f"corrected join ({int(cl.n.sum()):,} shots)")
    for i, (u, v) in enumerate(zip(nv.efg, cl.efg)):
        a.text(i - w / 2, 100 * u + 0.4, f"{100 * u:.1f}", ha="center", fontsize=8, color="#444444")
        a.text(i + w / 2, 100 * v + 0.4, f"{100 * v:.1f}", ha="center", fontsize=8, color=PERGAME)
    a.set_xticks(x); a.set_xticklabels(["Q1\ntightest", "Q2", "Q3", "Q4\nwidest"])
    a.set_xlabel("Offensive-spacing quartile")
    a.set_ylabel("Effective field-goal percentage (%)"); a.set_ylim(40, 62); a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", color="#DDDDDD", lw=0.6)
    a.set_title("Clock alignment removes the apparent spacing\u2013efficiency gradient"); a.legend(frameon=False, loc="upper left")
    fig.tight_layout(); save(fig, "FIG1_naive_vs_corrected_spacing_efg")
    return {"naive_efg": [round(float(v), 4) for v in nv.efg], "corrected_efg": [round(float(v), 4) for v in cl.efg],
            "n_naive": int(nv.n.sum()), "n_corrected": int(cl.n.sum()), "three_point_share_panel": "not shown (presentation-only)"}


def fig2() -> dict:
    G = pd.read_csv(R / "results" / "global_shift_by_game.csv", dtype={"game_id": str})
    S = json.load(open(R / "results" / "global_shift_summary.json"))["universe"]["all_calibratable"]
    SC = json.load(open(R / "results" / "global_shift_screens.json"))
    T = json.load(open(R / "results" / "temporal_semantic_2x2.json"))["metrics"]["M1"]
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8))
    # A — ECDF of per-game held-out agreement
    for m, lab, c in (("M0", "naive equal-clock join", NAIVE), ("M1", "fixed +4 s shift", SHIFT), ("M2", "game-specific calibration", PERGAME)):
        xs = np.sort(G[f"to_rate_{m}"].dropna().values)
        ax[0].plot(xs, np.linspace(0, 1, len(xs)), color=c, lw=2, label=f"{lab}: pooled {S[m]['pooled']:.3f}")
    ax[0].axvline(0.90, color="#BBBBBB", lw=0.9, ls=":"); ax[0].text(0.905, 0.04, "0.90", fontsize=8, color="#777777")
    ax[0].set_xlabel("Held-out turnover-team agreement, per game (fraction)"); ax[0].set_ylabel(f"Cumulative share of {S['M0']['n_games']} games")
    ax[0].set_title("A. Validation on held-out turnovers"); ax[0].legend(frameon=False, loc="upper left"); ax[0].set_xlim(0, 1.02); ax[0].set_ylim(0, 1.02)
    # B — wrong-state attribution
    labels = ["pre-shot window\nattributed to\nwrong team", "pre-turnover window\nattributed to\nwrong team", "screen onset\nappears < 0.5 s\ninto possession"]
    naive = [100 * S["M0"]["shot_wrong_team_rate"], 100 * S["M0"]["turnover_wrong_team_rate"], 100 * SC["M0"]["frac_onset_lt_0.5s"]]
    corr = [100 * S["M1"]["shot_wrong_team_rate"], 100 * S["M1"]["turnover_wrong_team_rate"], 100 * SC["M1"]["frac_onset_lt_0.5s"]]
    x = np.arange(3); w = 0.38
    ax[1].bar(x - w / 2, naive, w, color=NAIVE, label="naive equal-clock join"); ax[1].bar(x + w / 2, corr, w, color=SHIFT, label="fixed +4 s shift")
    for i, (u, v) in enumerate(zip(naive, corr)):
        ax[1].text(i - w / 2, u + 1.2, f"{u:.1f}%", ha="center", fontsize=8); ax[1].text(i + w / 2, v + 1.2, f"{v:.1f}%", ha="center", fontsize=8, color=SHIFT)
    ax[1].set_xticks(x); ax[1].set_xticklabels(labels, fontsize=8); ax[1].set_ylabel("Share of events (%)"); ax[1].set_ylim(0, 80)
    ax[1].set_title("B. Downstream state-assignment errors before / after the shift"); ax[1].legend(frameon=False)
    # C — the two offsetting errors, plotted as paired differences (axis includes zero; no truncated bars)
    diffs = [("clock error\n(naive \u2212 corrected clock)", T["paired_A_minus_C"], T["std_diff_A_minus_C_over_sdD"], SHIFT),
             ("non-live frames\n(all \u2212 live-only frames)", T["paired_A_minus_B"], T["std_diff_A_minus_B_over_sdD"], LIVE),
             ("net: naive, unfiltered\nvs corrected, live-only", T["paired_A_minus_D"], T["std_diff_A_minus_D_over_sdD"], PERGAME)]
    y = np.arange(3)[::-1]
    ax[2].axvline(0, color="#888888", lw=1)
    for yi, (_, v, sd, c) in zip(y, diffs):
        ax[2].plot([0, v], [yi, yi], color=c, lw=2.4, solid_capstyle="round", zorder=2)
        ax[2].plot([v], [yi], "o", color=c, ms=9, zorder=3)
        ax[2].text(v + (0.03 if v >= 0 else -0.03), yi + 0.17, f"{v:+.2f} ft/s  ({sd:+.2f} SD)",
                   ha="left" if v >= 0 else "right", va="bottom", fontsize=8.5, color=c)
    ax[2].set_yticks(y); ax[2].set_yticklabels([n for n, _, _, _ in diffs], fontsize=8)
    ax[2].tick_params(axis="y", length=0)
    ax[2].set_ylim(-0.6, 2.6); ax[2].set_xlim(-0.55, 0.55)
    ax[2].set_xlabel("Difference in mean offensive-player speed per possession (ft/s)")
    ax[2].set_title("C. Two errors cancel in aggregate speed")
    ax[2].text(0.02, 0.06, "cell means (ft/s):  A naive/all " + f"{T['mean_A']:.2f}" + "   B naive/live " + f"{T['mean_B']:.2f}"
                           + "\n                              C corrected/all " + f"{T['mean_C']:.2f}" + "   D corrected/live " + f"{T['mean_D']:.2f}",
               transform=ax[2].transAxes, fontsize=7.6, va="bottom", ha="left", color="#555555",
               bbox=dict(boxstyle="round", fc="white", ec="#DDDDDD"))
    for a in ax[:2]: a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", color="#DDDDDD", lw=0.6, alpha=0.8)
    ax[2].spines[["top", "right", "left"]].set_visible(False); ax[2].grid(axis="x", color="#DDDDDD", lw=0.6, alpha=0.8)
    fig.tight_layout(); save(fig, "FIG2_measurement_resource_evidence")
    return {"pooled": {m: round(S[m]["pooled"], 4) for m in ("M0", "M1", "M2")}, "n_games": S["M0"]["n_games"],
            "wrong_team_shot": [round(S["M0"]["shot_wrong_team_rate"], 4), round(S["M1"]["shot_wrong_team_rate"], 4)],
            "wrong_team_turnover": [round(S["M0"]["turnover_wrong_team_rate"], 4), round(S["M1"]["turnover_wrong_team_rate"], 4)],
            "onset_lt_0p5": [round(SC["M0"]["frac_onset_lt_0.5s"], 4), round(SC["M1"]["frac_onset_lt_0.5s"], 4)],
            "speed_cells": {k: round(T[f"mean_{k}"], 3) for k in "ABCD"},
            "speed_diffs_sd": {"A_minus_C": round(T["std_diff_A_minus_C_over_sdD"], 3), "A_minus_B": round(T["std_diff_A_minus_B_over_sdD"], 3), "A_minus_D": round(T["std_diff_A_minus_D_over_sdD"], 3)}}


CAPTION1 = ("Figure 1. Clock alignment removes the apparent spacing\u2013efficiency gradient (public 2015-16 SportVU corpus joined to stats.nba.com play-by-play). "
            "Shots are grouped into quartiles of offensive spacing, measured as the mean five-player convex-hull area over the two-second tracking window at the shot. "
            "Under the naive equal-clock join (grey; 27,563 shots) effective field-goal percentage rises from 47.8% in the tightest quartile to 57.2% in the widest; "
            "under the corrected join (blue; 64,764 shots, 437 validated games) the gradient is absent (52.4 / 49.8 / 49.1 / 50.5%). "
            "The scorer-latency phenomenon and the original 10-game eFG example were first shown by the ismayc/tracking-study repository; "
            "this figure is its season-scale generalization."
            " A matched-shot analysis on the 26,177 shots common to both joins reaches the same qualitative conclusion and is reported in docs/validation/MATCHED_SHOT_VALIDATION.md.")
CAPTION2 = ("Figure 2. Measurement and resource evidence (631 calibratable games). (A) Cumulative distribution over games of held-out turnover-team agreement, "
            "the share of turnovers whose pre-event tracking window is attributed to the team charged with the turnover; turnovers were never used to choose "
            "an offset. Naive equal-clock join 0.393 pooled, fixed +4 s shift 0.942, game-specific calibration 0.932 (16,943 held-out turnovers). "
            "(B) Share of events whose two-second pre-event window is attributed to the wrong team (shots, turnovers) and share of detected on-ball screens "
            "whose onset appears within 0.5 s of the possession start (7,625 screens, 301 games), before and after the +4 s shift. "
            "(C) The two offsetting errors as paired differences between the cells of a temporal × semantic design (301 games, 56,033 possessions): "
            "clock misalignment (naive − corrected clock) inflates mean offensive-player speed by 0.35 ft/s (+0.22 SD of cell D) while stopped-clock "
            "frames (all − live-only frames) deflate it by 0.33 ft/s (−0.20 SD), so the naive, unfiltered value sits within 0.03 SD of the corrected, "
            "live-only value (net +0.05 ft/s). Cell means: A naive/all 6.97, B naive/live 7.30, C corrected/all 6.63, D corrected/live 6.92 ft/s. "
            "SD = standard deviation across possessions of cell D.")


if __name__ == "__main__":
    v1 = fig1(); v2 = fig2()
    (OUT / "FIG1_naive_vs_corrected_spacing_efg.caption.txt").write_text(CAPTION1 + "\n")
    (OUT / "FIG2_measurement_resource_evidence.caption.txt").write_text(CAPTION2 + "\n")
    (OUT / "plotted_values.json").write_text(json.dumps({"fig1": v1, "fig2": v2}, indent=2))
    print(json.dumps({"fig1": v1, "fig2": v2}, indent=1))
