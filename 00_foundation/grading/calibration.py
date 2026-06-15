"""
Magnitude calibration (L3-GRADING-SPEC §5.1).

Compare the card's recovered `elevation_ratio` against the planted value elevation in
L1's OWN reference frame — `cat_value_mult[planted_cat] / geomean(all cat_value_mult)`.
L1's elevation_ratio is geomean-relative (sum-to-zero log centering), so the absolute
multiplier is unidentifiable and is NOT the target; comparing like-for-like is the
only meaningful bias. At this evidence strength EB attenuation is negligible, so the
like-for-like bias is near zero (not a downward ~10% — that figure was a reference-frame
artifact of comparing against the absolute multiplier). We REPORT bias and dispersion;
we do NOT assert zero (§5.1). Recorded over TP instances only — where the recovered
category equals the planted one, so elevation_ratio actually estimates the target.
"""

from __future__ import annotations

import statistics as st

from . import ground_truth as gt


def magnitude_record(manifest: dict, card: dict) -> dict:
    """Per-instance magnitude comparison in the like-for-like (geomean-relative) frame.
    Also records the absolute-frame offset, explicitly labeled as NOT a bias."""
    planted_mag = gt.planted_magnitude(manifest)              # geomean-relative (the target)
    est = float(card["recovered_wedge_category"]["elevation_ratio"])
    planted_abs = gt.planted_magnitude_absolute(manifest)
    return {
        "planted_mag": planted_mag,
        "elevation_ratio": est,
        "abs_bias": est - planted_mag,
        "rel_bias": (est - planted_mag) / planted_mag if planted_mag else None,
        # reference-frame OFFSET vs the absolute multiplier — a frame artifact, NOT a bias
        "reference_frame_offset_vs_absolute": {
            "planted_mag_absolute": planted_abs,
            "rel_offset": (est - planted_abs) / planted_abs if planted_abs else None,
        },
    }


def aggregate_bias(records: list[dict]) -> dict:
    """Aggregate magnitude bias across instances in the like-for-like frame (near-zero
    expected; not asserted). The absolute-frame offset is reported separately and
    explicitly flagged as a reference-frame artifact, not a bias."""
    if not records:
        return {"n": 0, "note": "no TP instances to calibrate magnitude"}
    ab = [r["abs_bias"] for r in records]
    rb = [r["rel_bias"] for r in records if r["rel_bias"] is not None]
    off = [r["reference_frame_offset_vs_absolute"]["rel_offset"]
           for r in records if r["reference_frame_offset_vs_absolute"]["rel_offset"] is not None]
    return {
        "n": len(records),
        "frame": "like-for-like (geomean-relative)",
        "mean_abs_bias": st.mean(ab),
        "stdev_abs_bias": st.pstdev(ab) if len(ab) > 1 else 0.0,
        "mean_rel_bias": st.mean(rb) if rb else None,
        "stdev_rel_bias": st.pstdev(rb) if len(rb) > 1 else 0.0,
        # NOT a bias — included for transparency, labeled
        "absolute_reference_frame_offset_not_a_bias": {
            "mean_rel_offset": st.mean(off) if off else None,
            "stdev_rel_offset": st.pstdev(off) if len(off) > 1 else 0.0,
        },
    }
