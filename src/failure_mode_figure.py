#!/usr/bin/env python3
"""FIG_ALIGNMENT_FAILURE_MODES: one medoid game per frozen taxonomy class (rule: configs/failure_mode_examples.yaml).
Curves: shot-calibration agreement (shared table curve_rates) and held-out turnover agreement per lead (data/global_shift cache,
computed by src/global_shift.py with the unchanged labeler). Marks: 0 s, +4 s, per-game lead (and half leads for DRIFTING).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd, yaml
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

R = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((R / "configs" / "failure_mode_examples.yaml").read_text())
LEADS = [x * 0.5 for x in range(17)]


def main() -> int:
    T = pd.read_csv(R / "results" / "taxonomy_by_game.csv", dtype={"game_id": str})
    T = T[T.curve_rates.notna() & (T.curve_rates != "")]; T["curve"] = T.curve_rates.map(lambda s: np.array([float(x) for x in s.split("|")]))
    sel = {}
    for cls in CFG["classes"]:
        g = T[T.taxonomy_class == cls].sort_values("game_id"); C = np.stack(g.curve.values); dist = np.abs(C[:, None, :] - C[None, :, :]).sum(axis=2).sum(axis=1)
        sel[cls] = g.iloc[int(np.argmin(dist))]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), dpi=170, sharey=True); C1, C2, G = "#2E6F9E", "#C9622B", "#777777"
    meta = {}
    for ax, cls in zip(axes, CFG["classes"]):
        r = sel[cls]; to = json.load(open(R / "data" / "global_shift" / f"{r.game_id}.json"))["to_curve"]; tor = [a / n if n else np.nan for a, n in to]
        ax.plot(LEADS, r.curve, "o-", color=C1, ms=3, lw=1.4, label="shot agreement (calibration)"); ax.plot(LEADS, tor, "s--", color=C2, ms=3, lw=1.2, label="turnover agreement (held out)")
        ax.axvline(0.0, color=G, lw=0.8, ls=":"); ax.axvline(4.0, color=G, lw=1.2, ls="--"); ax.axvline(float(r.calibrated_lead_s), color=C1, lw=1.2)
        ax.text(4.0, 0.06, "+4 s", ha="center", fontsize=7, color=G); ax.text(float(r.calibrated_lead_s), 0.13, f"game lead {r.calibrated_lead_s:.1f}", ha="center", fontsize=7, color=C1)
        if cls == "DRIFTING":
            for h, L in (("H1", r.lead_H1), ("H2", r.lead_H2)):
                ax.axvline(float(L), color="#6A994E", lw=0.9, ls="-."); ax.text(float(L), 0.22 if h == "H1" else 0.30, f"{h} {L:.1f}", ha="center", fontsize=6.5, color="#6A994E")
        ax.set_title(f"{cls}\n{r.stem} (plateau {r.plateau_width_s_within_0p02:.1f} s)", fontsize=8); ax.set_xlabel("candidate lead (s)", fontsize=8); ax.set_ylim(0, 1.02); ax.grid(color="#DDDDDD", lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        meta[cls] = {"game_id": r.game_id, "stem": r.stem, "calibrated_lead_s": float(r.calibrated_lead_s), "plateau_width_s": float(r.plateau_width_s_within_0p02), "to_rate_at_0": tor[0], "to_rate_at_4": tor[8], "to_rate_at_lead": tor[int(round(r.calibrated_lead_s / 0.5))], "lead_H1": float(r.lead_H1), "lead_H2": float(r.lead_H2)}
    axes[0].set_ylabel("agreement with PBP team", fontsize=8); axes[0].legend(fontsize=7, frameon=False, loc="lower right")
    fig.suptitle("Alignment curves by frozen taxonomy class (medoid game per class; selection uses only curve shape). Vertical: 0 s, +4 s global, per-game lead.", fontsize=8.5)
    fig.tight_layout(); fig.savefig(R / "figures" / "FIG_ALIGNMENT_FAILURE_MODES.png", bbox_inches="tight"); plt.close(fig)
    json.dump(meta, open(R / "results" / "failure_mode_examples.json", "w"), indent=2); print(json.dumps(meta, indent=1)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
