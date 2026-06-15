"""
L3 grading layer — machine-scores the L1 recovery card against the ground truth.

L3 is the SOLE sanctioned reader of the answer manifest, and the
grade is the deliverable (L3-GRADING-SPEC §1, §2). It consumes the L1 card as a
black box (persisted JSON), never importing or re-running L1.

v1 scope (spec §4, §5.1): decision-gated TP/FP/FN + magnitude calibration. TN is
not gradable in V1 (the generator always plants a wedge — §4.3) and §5.2 post_prob
calibration is deferred (the card exposes a posterior only for the recovered wedge,
not per category — §8.2). Extension points are left clean, not faked.

Modules:
  ground_truth — the SINGLE accessor to the answer + field helpers (spec §1)
  card_io      — load a persisted card as data (no L1 import)
  provenance   — pure observation-hash primitive (replicated, not imported from L1)
  firewall     — re-verify the card's provenance attestation (spec §4.4)
  match        — decision-gated, category-exact, segment-tolerant predicate (spec §4.1)
  calibration  — magnitude calibration vs the planted value elevation (spec §5.1)
  grade        — aggregate over a SET of (manifest, card) pairs
  run          — entry point
"""

from .ground_truth import load, planted_category, planted_magnitude, MANIFEST_NAME
from .card_io import load_card
from .provenance import observation_hash
from .firewall import reverify
from .match import classify, segment_crosscheck
from .calibration import magnitude_record, aggregate_bias
from .grade import Case, grade_cases

__all__ = [
    "load", "planted_category", "planted_magnitude", "MANIFEST_NAME",
    "load_card", "observation_hash", "reverify",
    "classify", "segment_crosscheck", "magnitude_record", "aggregate_bias",
    "Case", "grade_cases",
]
