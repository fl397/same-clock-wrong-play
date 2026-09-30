"""Vendored unchanged from the screen-detection study: the frozen screen-candidate mask.
Used only by the screen-consequence stage, which needs withheld screen-detection tables (docs/REPRODUCIBILITY.md)."""
import pandas as pd


def candidate_mask(fe: pd.DataFrame, c: dict) -> pd.Series:
    m = pd.Series(True, index=fe.index)
    if "ST" in c: m &= fe.screener_speed_at_t0 <= c["ST"]
    if "SB" in c: m &= fe.screener_slow_frac_pre_10 >= c["SB"]
    if "PI" in c: m &= (fe.impedance_perp_dist <= c["PI"]) & fe.impedance_proj_fraction.between(0.0, 1.0)
    if "CD" in c: m &= fe.contact_persist_s >= c["CD"]
    return m
