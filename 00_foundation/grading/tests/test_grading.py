"""
Pytest suite for the L3 grading layer (L3-GRADING-SPEC §7 invariants + §4/§5.1).

Naming: test_<subject>_<property>; docstrings state the invariant. Uses synthetic
(manifest, card) pairs written to tmp — L3 never generates real pairs (that needs
L1) and never imports L1.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from grading import ground_truth, provenance, match, calibration
from grading.grade import Case, grade_cases

CATS = ("C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7")


def _make_manifest(planted_cat="C3", mag=2.5, anchor_seg="S2"):
    m = {"wedge": {"segment": anchor_seg, "category": planted_cat},
         "cat_value_mult": {c: 1.0 for c in CATS},
         "true_cat_w": {c: 0.0 for c in CATS}}
    m["cat_value_mult"][planted_cat] = mag
    m["true_cat_w"][planted_cat] = -0.5
    return m


def _make_card(decision=True, recovered="C3", elevation=2.3, manifest_read=False,
               obs_hash="", segments=("S1", "S2")):
    return {"provenance": {"observation_hash": obs_hash, "manifest_read": manifest_read},
            "wedge_exists": {"decision": decision},
            "recovered_wedge_category": {"category_id": recovered, "elevation_ratio": elevation,
                                         "cell_breakdown": [{"segment_id": s} for s in segments]}}


def _write_case(tmp: Path, name: str, *, hash_ok=True, **card_kw) -> Case:
    d = tmp / name
    d.mkdir(parents=True)
    acc, opp = d / "accounts.csv", d / "opportunities.csv"
    acc.write_text("AccountId,Segment,Category\nA1,S1,C3\nA2,S2,C0\n")
    opp.write_text("OppId,AccountId,Stage,Amount\nO1,A1,06 - Closed Won,1000\n")
    (d / ground_truth.MANIFEST_NAME).write_text(json.dumps(_make_manifest()))
    h = provenance.observation_hash(acc, opp) if hash_ok else "deadbeef"
    (d / "recovery_card.json").write_text(json.dumps(_make_card(obs_hash=h, **card_kw)))
    return Case(str(d / ground_truth.MANIFEST_NAME), str(d / "recovery_card.json"),
                str(acc), str(opp), label=name)


# --------------------------------------------------------------------------- #
# match predicate (§4.1)
# --------------------------------------------------------------------------- #
def test_match_tp_fp_fn_outcomes():
    """decision-gated predicate yields TP (right cat), FP (wrong cat), FN (no decision)."""
    m = _make_manifest(planted_cat="C3")
    assert match.classify(m, _make_card(decision=True, recovered="C3")) == "TP"
    assert match.classify(m, _make_card(decision=True, recovered="C5")) == "FP"
    assert match.classify(m, _make_card(decision=False, recovered="C3")) == "FN"


def test_decision_false_never_tp_or_fp():
    """INV: a decision=False card is never positive, even if it names the right category."""
    m = _make_manifest(planted_cat="C3")
    for recovered in ("C3", "C5", "C3"):
        assert match.classify(m, _make_card(decision=False, recovered=recovered)) == "FN"


def test_segment_is_not_a_tp_gate():
    """INV: segment-tolerant — a correct-category card grades TP even when its
    cell_breakdown segments exclude the manifest's segment anchor."""
    m = _make_manifest(planted_cat="C3", anchor_seg="S2")
    card = _make_card(decision=True, recovered="C3", segments=("S1",))  # no S2 anchor
    assert match.classify(m, card) == "TP"
    cc = match.segment_crosscheck(m, card)
    assert cc["planted_segment_anchor"] == "S2" and "S2" not in cc["recovered_segments"]


# --------------------------------------------------------------------------- #
# firewall re-verification (§4.4)
# --------------------------------------------------------------------------- #
def test_firewall_rejects_hash_mismatch_not_graded(tmp_path):
    """INV: a card failing observation_hash re-verification is rejected, never graded."""
    rep = grade_cases([_write_case(tmp_path, "bad", hash_ok=False, decision=True, recovered="C3")])
    assert rep["rejected"] == 1 and rep["graded"] == 0
    assert rep["confusion"] == {"TP": 0, "FP": 0, "FN": 0, "TN": "pending no-wedge profile"}
    assert rep["per_case"][0]["status"] == "REJECTED"


def test_firewall_rejects_manifest_read_true(tmp_path):
    """INV: manifest_read != false => rejected (the card claims it read the answer)."""
    rep = grade_cases([_write_case(tmp_path, "leak", manifest_read=True, decision=True, recovered="C3")])
    assert rep["rejected"] == 1 and rep["graded"] == 0


def test_firewall_passes_consistent_pair_then_grades(tmp_path):
    """A consistent pair (hash matches, manifest_read=false) is graded normally."""
    rep = grade_cases([_write_case(tmp_path, "ok", decision=True, recovered="C3")])
    assert rep["rejected"] == 0 and rep["confusion"]["TP"] == 1


# --------------------------------------------------------------------------- #
# aggregation + reconciliation (§4.1, §7)
# --------------------------------------------------------------------------- #
def test_counts_reconcile_over_instance_set(tmp_path):
    """INV: TP+FP+FN+rejected == total cases; grading is over the set."""
    cases = [
        _write_case(tmp_path, "tp", decision=True, recovered="C3"),
        _write_case(tmp_path, "fp", decision=True, recovered="C5"),
        _write_case(tmp_path, "fn", decision=False, recovered="C3"),
        _write_case(tmp_path, "rej", hash_ok=False, decision=True, recovered="C3"),
    ]
    rep = grade_cases(cases)
    c = rep["confusion"]
    assert (c["TP"] + c["FP"] + c["FN"] + rep["rejected"]) == rep["n_cases"] == 4
    assert rep["reconciliation_ok"] is True
    assert len(rep["per_case"]) == 4


def test_tn_marked_pending_no_wedge_profile(tmp_path):
    """V1 cannot grade TN (always-planted) — it is reported as pending, not faked."""
    rep = grade_cases([_write_case(tmp_path, "tp", decision=True, recovered="C3")])
    assert rep["confusion"]["TN"] == "pending no-wedge profile"


# --------------------------------------------------------------------------- #
# magnitude calibration (§5.1)
# --------------------------------------------------------------------------- #
def test_magnitude_bias_reported_not_asserted_zero():
    """INV: bias is reported (mean + dispersion); attenuated estimate => negative
    bias — not asserted to be zero."""
    m = _make_manifest(planted_cat="C3", mag=3.0)
    recs = [calibration.magnitude_record(m, _make_card(recovered="C3", elevation=e))
            for e in (2.4, 2.7, 2.9)]
    agg = calibration.aggregate_bias(recs)
    assert agg["n"] == 3
    assert agg["mean_abs_bias"] < 0           # attenuated below planted 3.0
    assert "stdev_abs_bias" in agg and "mean_rel_bias" in agg


def test_magnitude_only_over_tp(tmp_path):
    """Magnitude calibration counts only TP instances (FP recovers a different cat)."""
    cases = [_write_case(tmp_path, "tp", decision=True, recovered="C3", elevation=2.0),
             _write_case(tmp_path, "fp", decision=True, recovered="C5", elevation=9.9)]
    rep = grade_cases(cases)
    assert rep["magnitude_calibration"]["n"] == 1   # only the TP contributes


# --------------------------------------------------------------------------- #
# accessor + firewall static invariants (§7)
# --------------------------------------------------------------------------- #
def test_ground_truth_accessor_loads_and_indexes(tmp_path):
    """The accessor loads the manifest and field helpers index the wedge."""
    p = tmp_path / ground_truth.MANIFEST_NAME
    p.write_text(json.dumps(_make_manifest(planted_cat="C4", mag=4.2)))
    m = ground_truth.load(p)
    assert ground_truth.planted_category(m) == "C4"
    assert ground_truth.planted_magnitude(m) == 4.2


def _grading_sources():
    pkg = Path(__file__).resolve().parents[1]
    return {p.name: p.read_text(encoding="utf-8") for p in pkg.glob("*.py")}


def test_single_accessor_manifest_name_only_in_accessor():
    """INV: the manifest filename literal lives only in the accessor module."""
    for name, src in _grading_sources().items():
        if name == "ground_truth.py":
            continue
        assert "_ground_truth" not in src, f"{name} references the manifest file directly"


def test_no_l1_import_in_grading():
    """INV: L3 imports no L1 internals (the card is data only)."""
    for name, src in _grading_sources().items():
        assert not re.search(r"\b(import|from)\s+recovery\b", src), f"{name} imports L1"
        assert "from recovery" not in src and "import recovery" not in src, f"{name} imports L1"


def test_no_hardcoded_category_or_magnitude():
    """INV (forward-compat): no hardcoded wedge identity or magnitude literal."""
    for name, src in _grading_sources().items():
        assert "Cat-" not in src, f"{name} hardcodes a category id"
        assert "MidMarket" not in src, f"{name} hardcodes a segment id"
        planted = [m.start() for m in re.finditer(r"3\.2", src)
                   if src[m.start() - 1] not in "§.0123456789"
                   and not src[m.end():m.end() + 1].isdigit()]
        assert not planted, f"{name} hardcodes the planted magnitude 3.2"
