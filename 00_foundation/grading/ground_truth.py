"""
The single ground-truth accessor (L3-GRADING-SPEC §1).

THIS is the only place in L3 that opens the answer file. Recovery-grading (v1)
and any future decision-grading increment must read the manifest through here —
one mouth to the answer, audited in one place. Field access is via the helpers
below, which index the manifest dict (never hardcoding the wedge identity or
magnitude, so the grader is forward-compatible across profiles — §6, §7).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

MANIFEST_NAME = "_ground_truth.json"


def load(manifest_path) -> dict:
    """Load the synthetic answer key. The sole sanctioned manifest read in L3."""
    return json.loads(Path(manifest_path).read_text())


def planted_category(manifest: dict) -> str:
    """The planted wedge category id (profile constant; indexed, never hardcoded)."""
    return manifest["wedge"]["category"]


def _geomean(values) -> float:
    vals = list(values)
    return math.exp(sum(math.log(v) for v in vals) / len(vals))   # multipliers are > 0


def planted_magnitude(manifest: dict) -> float:
    """The planted VALUE elevation in L1's reference frame (spec §5.1):
    cat_value_mult[planted_cat] / geomean(all cat_value_mult).

    L1's elevation_ratio is geomean-relative (sum-to-zero log centering), under which
    the ABSOLUTE multiplier is unidentifiable — so the geomean-relative form is the
    correct, like-for-like calibration target. Bound to the value surface
    (cat_value_mult), never to true_cat_w (the conversion / blind-spot cause)."""
    cvm = manifest["cat_value_mult"]
    return float(cvm[planted_category(manifest)] / _geomean(cvm.values()))


def planted_magnitude_absolute(manifest: dict) -> float:
    """Raw cat_value_mult[planted_cat]. Reported ONLY as a labeled reference-frame
    offset — it is not a calibration target (not identifiable under sum-to-zero)."""
    return float(manifest["cat_value_mult"][planted_category(manifest)])
