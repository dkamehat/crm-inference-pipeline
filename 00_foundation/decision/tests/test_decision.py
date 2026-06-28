"""
Pytest suite for the L2 decision layer (L2-DECISION-SPEC §3, §4).

Naming: test_<subject>_<property>; docstrings state the property. Uses small
synthetic frames (no manifest, no answer key) — L2 never reads the answer. The
properties checked are the spec's by-construction guarantees: lexicographic key
priority, full-universe coverage, determinism, and the firewall attestation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from decision import io, card as _card
from decision.rank import rank_accounts, RankedAccount, W1, W2, W3, SEGMENT_TIER


def _accounts(rows):
    """rows: list of (AccountId, Segment, Category)."""
    return pd.DataFrame(rows, columns=["AccountId", "Segment", "Category"])


# --------------------------------------------------------------------------- #
# key 1 — category dominates (the decision)
# --------------------------------------------------------------------------- #
def test_rank_category_block_above_everything():
    """Every recovered-category account outranks every non-category account —
    even an Enterprise non-member with zero wins (spec §4.2 key 1 dominates)."""
    acc = _accounts([("a", "SMB", "Cat-D"),          # member, lowest tier, but in category
                     ("b", "Enterprise", "Cat-A")])  # non-member, highest tier, 0 wins
    ranked = rank_accounts(acc, {}, "Cat-D")
    assert ranked[0].account_id == "a" and ranked[0].in_recovered_category
    assert ranked[1].account_id == "b" and not ranked[1].in_recovered_category


# --------------------------------------------------------------------------- #
# key 2 — within the block, higher segment tier first
# --------------------------------------------------------------------------- #
def test_rank_segment_tier_orders_within_block():
    """Within the recovered category, Enterprise > MidMarket > SMB (spec §4.2 key 2)."""
    acc = _accounts([("smb", "SMB", "Cat-D"),
                     ("ent", "Enterprise", "Cat-D"),
                     ("mm", "MidMarket", "Cat-D")])
    order = [r.account_id for r in rank_accounts(acc, {}, "Cat-D")]
    assert order == ["ent", "mm", "smb"]


# --------------------------------------------------------------------------- #
# key 3 — within tier, under-penetration (fewer wins) first
# --------------------------------------------------------------------------- #
def test_rank_underpenetration_orders_within_tier():
    """Same category and tier: fewer Closed-Won ranks first — 'high value, not worked'
    surfaces to the top (spec §4.2 key 3)."""
    acc = _accounts([("worked", "MidMarket", "Cat-D"),
                     ("fresh", "MidMarket", "Cat-D")])
    ranked = rank_accounts(acc, {"worked": 5, "fresh": 0}, "Cat-D")
    assert [r.account_id for r in ranked] == ["fresh", "worked"]


def test_rank_lexicographic_no_key3_overturns_key2():
    """Key priority is strict: an SMB with 0 wins can never outrank a MidMarket with
    many wins inside the block (penetration must not overturn tier — spec §4.2)."""
    acc = _accounts([("smb0", "SMB", "Cat-D"),         # tier 1, 0 wins
                     ("mm9", "MidMarket", "Cat-D")])   # tier 2, 9 wins
    ranked = rank_accounts(acc, {"smb0": 0, "mm9": 9}, "Cat-D")
    assert [r.account_id for r in ranked] == ["mm9", "smb0"]


# --------------------------------------------------------------------------- #
# full universe + determinism (spec §3)
# --------------------------------------------------------------------------- #
def test_rank_covers_full_universe():
    """The ranking covers every account exactly once with contiguous ranks 1..N
    (full-universe rule — what makes precision@K non-trivial, spec §3/§5.4)."""
    acc = _accounts([(f"a{i}", "SMB", "Cat-A") for i in range(7)])
    ranked = rank_accounts(acc, {}, "Cat-D")
    assert len(ranked) == 7
    assert [r.rank for r in ranked] == list(range(1, 8))
    assert {r.account_id for r in ranked} == {f"a{i}" for i in range(7)}


def test_rank_deterministic_tiebreak_by_account_id():
    """Identical category/tier/n_won ties break by AccountId, so the ranking is
    reproducible regardless of input row order (spec §4.2)."""
    rows = [("a3", "SMB", "Cat-D"), ("a1", "SMB", "Cat-D"), ("a2", "SMB", "Cat-D")]
    a = [r.account_id for r in rank_accounts(_accounts(rows), {}, "Cat-D")]
    b = [r.account_id for r in rank_accounts(_accounts(list(reversed(rows))), {}, "Cat-D")]
    assert a == b == ["a1", "a2", "a3"]


def test_rank_unknown_segment_tier_zero():
    """An unrecognized Segment label gets tier 0 (ranked last within its block),
    never crashing the ranker (spec §4.1 — observable assumption, defensive)."""
    acc = _accounts([("known", "SMB", "Cat-D"), ("weird", "Platinum", "Cat-D")])
    ranked = rank_accounts(acc, {}, "Cat-D")
    assert SEGMENT_TIER.get("Platinum", 0) == 0
    assert [r.account_id for r in ranked] == ["known", "weird"]


# --------------------------------------------------------------------------- #
# artifact / firewall attestation (spec §3 output, §6)
# --------------------------------------------------------------------------- #
def test_ranking_artifact_schema_and_attestation():
    """The emitted ranking carries the firewall attestation (manifest_read=false +
    observation_hash) and a complete row schema (spec §3 output contract)."""
    acc = _accounts([("a", "MidMarket", "Cat-D"), ("b", "SMB", "Cat-A")])
    ranked = rank_accounts(acc, {"a": 1}, "Cat-D")
    art = _card.build_ranking(ranked, observation_hash="abc123",
                              recovered_category="Cat-D", weights=(W1, W2, W3))
    assert art["provenance"]["manifest_read"] is False
    assert art["provenance"]["observation_hash"] == "abc123"
    assert art["provenance"]["n_accounts"] == 2
    for key, typ in _card.RANKING_SCHEMA.items():
        assert isinstance(art[key], dict if isinstance(typ, dict) else typ)
    for key, typ in _card.ROW_SCHEMA.items():
        assert isinstance(art["ranking"][0][key], typ)


def test_io_won_counts_won_only(tmp_path):
    """Penetration counts Closed-Won only — Lost/open opps (which also carry Amount)
    must not inflate it (spec §4.1)."""
    opp = tmp_path / "opportunities.csv"
    opp.write_text("AccountId,Stage\n"
                   "a,06 - Closed Won\na,06 - Closed Won\n"
                   "a,07 - Closed Lost\nb,03 - Proposal\n")
    counts = io.won_counts(opp)
    assert counts == {"a": 2}


def test_io_recovered_category_reads_card(tmp_path):
    """L2 reads the recovered category from the card as data (no L1 re-run)."""
    card = tmp_path / "card.json"
    card.write_text('{"recovered_wedge_category": {"category_id": "Cat-D"}}')
    assert io.recovered_category(card) == "Cat-D"


def test_io_audit_columns_flags_truth_leak(tmp_path):
    """The column audit fires if a truth-like column name leaks into the observation."""
    acc, opp = tmp_path / "accounts.csv", tmp_path / "opportunities.csv"
    acc.write_text("AccountId,Segment,Category,true_value\na,SMB,Cat-A,9\n")
    opp.write_text("AccountId,Stage\na,06 - Closed Won\n")
    clean, hits = io.audit_columns(acc, opp)
    assert not clean and "true_value" in hits
