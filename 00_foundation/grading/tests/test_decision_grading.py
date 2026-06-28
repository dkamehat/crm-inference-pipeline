"""
Pytest suite for L3 decision-grading — precision@K (L2-DECISION-SPEC §5).

Synthetic (manifest, ranking, accounts) instances written to tmp; L3 reads the
answer only through ground_truth. The properties checked are the spec's: a correct
ranker beats the base rate by a wide margin, an answer-ignoring ranker collapses to
the base rate (the full-universe rule), precision degrades past the positive set,
and a ranking that fails firewall re-verification is rejected.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from grading import decision, provenance, firewall
from grading.decision_run import grade_dirs


def _manifest(planted="Cat-D"):
    return {"wedge": {"segment": "MidMarket", "category": planted},
            "cat_value_mult": {"Cat-A": 1.0, "Cat-D": 3.2}}


def _accounts_csv(n_pos, n_neg):
    lines = ["AccountId,Segment,Category"]
    lines += [f"p{i},MidMarket,Cat-D" for i in range(n_pos)]
    lines += [f"n{i},SMB,Cat-A" for i in range(n_neg)]
    return "\n".join(lines) + "\n"


def _ranking(account_ids, obs_hash="", manifest_read=False):
    return {"spec": "L2-DECISION-SPEC",
            "provenance": {"observation_hash": obs_hash, "manifest_read": manifest_read,
                           "recovered_category": "Cat-D"},
            "ranking": [{"AccountId": a, "rank": i + 1, "score": 0.0,
                         "in_recovered_category": a.startswith("p"),
                         "segment_tier": 2, "n_won": 0}
                        for i, a in enumerate(account_ids)]}


def test_positive_set_from_manifest(tmp_path):
    """The positive set is the accounts whose observed Category == planted category."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(3, 5))
    pos = decision.positive_set(_manifest(), acc)
    assert pos == {"p0", "p1", "p2"}


def test_precision_at_k_perfect_ranker_beats_base_rate(tmp_path):
    """A ranker that puts the positives first scores precision@K ≈ 1.0, far above the
    13%-style base rate (spec §5.4 pass signal)."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(20, 80))            # base rate 0.20
    pos = decision.positive_set(_manifest(), acc)
    ids = [f"p{i}" for i in range(20)] + [f"n{i}" for i in range(80)]
    rec = decision.grade_ranking(_manifest(), _ranking(ids), acc, ks=(10,))
    assert rec["base_rate"] == 0.20
    assert rec["precision_at_k"]["10"] == 1.0


def test_precision_at_k_answer_ignoring_ranker_collapses_to_base_rate(tmp_path):
    """An answer-ignoring ranking (positives interleaved like a random draw) scores
    precision@K ≈ base rate — the full-universe rule is what makes the metric a real
    test (spec §5.4)."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(20, 80))
    # every 5th account is a positive -> top-10 holds 2 positives -> 0.2 == base rate
    ids = []
    p = iter(f"p{i}" for i in range(20))
    n = iter(f"n{i}" for i in range(80))
    for i in range(100):
        ids.append(next(p) if i % 5 == 0 else next(n))
    rec = decision.grade_ranking(_manifest(), _ranking(ids), acc, ks=(10,))
    assert rec["precision_at_k"]["10"] == pytest.approx(rec["base_rate"])


def test_precision_degrades_beyond_positive_set(tmp_path):
    """Past the positive-set size precision must fall (only n_pos positives exist) —
    the K=200 sanity row of the spec sweep (spec §5.3)."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(20, 80))
    ids = [f"p{i}" for i in range(20)] + [f"n{i}" for i in range(80)]
    rec = decision.grade_ranking(_manifest(), _ranking(ids), acc, ks=(20, 40))
    assert rec["precision_at_k"]["20"] == 1.0       # exactly the positives
    assert rec["precision_at_k"]["40"] == 0.5       # 20 hits / 40


def test_precision_at_n_positives_is_ceiling(tmp_path):
    """At K = |positives|, a perfect ranker reaches precision = recall = 1.0."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(15, 85))
    ids = [f"p{i}" for i in range(15)] + [f"n{i}" for i in range(85)]
    rec = decision.grade_ranking(_manifest(), _ranking(ids), acc)
    assert rec["precision_at_n_positives"] == 1.0


def test_aggregate_means_across_seeds(tmp_path):
    """Aggregate reports mean precision@K over the common Ks across instances."""
    acc = tmp_path / "accounts.csv"
    acc.write_text(_accounts_csv(20, 80))
    perfect = decision.grade_ranking(_manifest(), _ranking(
        [f"p{i}" for i in range(20)] + [f"n{i}" for i in range(80)]), acc, ks=(10,))
    half = decision.grade_ranking(_manifest(), _ranking(
        [f"p{i}" for i in range(5)] + [f"n{i}" for i in range(15)]      # 5/10 in top-10
        + [f"p{i}" for i in range(5, 20)] + [f"n{i}" for i in range(15, 80)]), acc, ks=(10,))
    agg = decision.aggregate([perfect, half])
    assert agg["n"] == 2
    assert agg["mean_precision_at_k"]["10"] == pytest.approx(0.75)   # (1.0 + 0.5)/2


def _write_instance(tmp: Path, name: str, *, hash_ok=True, manifest_read=False) -> Path:
    d = tmp / name
    d.mkdir(parents=True)
    acc, opp = d / "accounts.csv", d / "opportunities.csv"
    acc.write_text(_accounts_csv(10, 40))
    opp.write_text("AccountId,Stage\np0,06 - Closed Won\n")
    (d / "_ground_truth.json").write_text(json.dumps(_manifest()))
    h = provenance.observation_hash(acc, opp) if hash_ok else "deadbeef"
    ids = [f"p{i}" for i in range(10)] + [f"n{i}" for i in range(40)]
    (d / "decision_ranking.json").write_text(json.dumps(
        _ranking(ids, obs_hash=h, manifest_read=manifest_read)))
    return d


def test_grade_dirs_grades_clean_instance(tmp_path):
    """A firewall-clean instance is graded (not rejected) and reconciles."""
    d = _write_instance(tmp_path, "seed_1000")
    report = grade_dirs([d])
    assert report["graded"] == 1 and report["rejected"] == 0
    assert report["reconciliation_ok"]
    assert report["aggregate"]["mean_precision_at_k"]["10"] == 1.0


def test_grade_dirs_rejects_firewall_violation(tmp_path):
    """A ranking with manifest_read=true is rejected, never graded (spec §6)."""
    d = _write_instance(tmp_path, "seed_bad", manifest_read=True)
    report = grade_dirs([d])
    assert report["graded"] == 0 and report["rejected"] == 1


def test_grade_dirs_rejects_hash_mismatch(tmp_path):
    """A ranking whose observation_hash does not match the CSVs is rejected (spec §6)."""
    d = _write_instance(tmp_path, "seed_tamper", hash_ok=False)
    report = grade_dirs([d])
    assert report["graded"] == 0 and report["rejected"] == 1
    assert "mismatch" in report["firewall"]["rejections"][0]["reasons"][0]
