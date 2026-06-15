"""
Magnitude calibration (L3-GRADING-SPEC §5.1).

Compare the card's recovered `elevation_ratio` against the planted value elevation
`cat_value_mult[planted_cat]`, across instances. Empirical-Bayes shrinkage attenuates
the estimate toward the prior, so the bias is expected to be bounded and non-positive
on average, shrinking as evidence strengthens. We REPORT bias and dispersion; we do
NOT assert zero bias (§5.1). Recorded over TP instances only — where the recovered
category equals the planted one, so elevation_ratio actually estimates planted_mag.
"""

from __future__ import annotations

import statistics as st

from . import ground_truth as gt


def magnitude_record(manifest: dict, card: dict) -> dict:
    """Per-instance magnitude comparison (call on TP instances)."""
    planted_mag = gt.planted_magnitude(manifest)
    est = float(card["recovered_wedge_category"]["elevation_ratio"])
    return {
        "planted_mag": planted_mag,
        "elevation_ratio": est,
        "abs_bias": est - planted_mag,
        "rel_bias": (est - planted_mag) / planted_mag if planted_mag else None,
    }


def aggregate_bias(records: list[dict]) -> dict:
    """Aggregate magnitude bias across instances (bounded, non-positive on average
    expected; not asserted)."""
    if not records:
        return {"n": 0, "note": "no TP instances to calibrate magnitude"}
    ab = [r["abs_bias"] for r in records]
    rb = [r["rel_bias"] for r in records if r["rel_bias"] is not None]
    return {
        "n": len(records),
        "mean_abs_bias": st.mean(ab),
        "stdev_abs_bias": st.pstdev(ab) if len(ab) > 1 else 0.0,
        "mean_rel_bias": st.mean(rb) if rb else None,
        "stdev_rel_bias": st.pstdev(rb) if len(rb) > 1 else 0.0,
    }
