"""
Decision-gated match predicate (L3-GRADING-SPEC §4.1).

Field-driven and seed-independent: the planted category is read by indexing
`wedge.category` (never hardcoded). Category-exact, SEGMENT-TOLERANT — the planted
structure is a category main effect spanning all segments, so segment is never a
TP gate; `cell_breakdown[].segment_id` is used only as a tolerant cross-check.

V1: a wedge is always planted (§4.3), so `decision == False` is the only
manifest-graded negative and resolves to FN. TN is not produced here (no no-wedge
instances exist — reported as pending by the aggregator).
"""

from __future__ import annotations

from . import ground_truth as gt

OUTCOMES = ("TP", "FP", "FN")


def classify(manifest: dict, card: dict) -> str:
    """Return one of TP / FP / FN. The recovered category is read ONLY when the
    existence gate is True, so a decision=False card can never be positive."""
    decision = bool(card["wedge_exists"]["decision"])
    if not decision:
        return "FN"                                   # V1: wedge always planted (§4.3)
    recovered = card["recovered_wedge_category"]["category_id"]
    return "TP" if recovered == gt.planted_category(manifest) else "FP"


def segment_crosscheck(manifest: dict, card: dict) -> dict:
    """Tolerant, informational only — NEVER a TP gate (§4.1). Reports the planted
    segment anchor vs the segments the card's cell_breakdown actually spans."""
    segs = [c.get("segment_id") for c in card["recovered_wedge_category"].get("cell_breakdown", [])]
    return {
        "planted_segment_anchor": manifest["wedge"]["segment"],
        "recovered_segments": segs,
        "spans_multiple_segments": len(set(segs)) > 1,
    }
