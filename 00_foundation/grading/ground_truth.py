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
from pathlib import Path

MANIFEST_NAME = "_ground_truth.json"


def load(manifest_path) -> dict:
    """Load the synthetic answer key. The sole sanctioned manifest read in L3."""
    return json.loads(Path(manifest_path).read_text())


def planted_category(manifest: dict) -> str:
    """The planted wedge category id (profile constant; indexed, never hardcoded)."""
    return manifest["wedge"]["category"]


def planted_magnitude(manifest: dict) -> float:
    """The planted VALUE elevation = cat_value_mult[planted_cat] (spec §4.2/§5.1).
    Bound to the value surface, never to true_cat_w (the conversion / blind-spot cause)."""
    return float(manifest["cat_value_mult"][planted_category(manifest)])
