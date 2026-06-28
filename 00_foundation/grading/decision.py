"""
L2 decision-grading — precision@K (L2-DECISION-SPEC §5, Option A).

L3 is the sole answer-reader. It builds the ground-truth positive set from the
manifest (accounts whose Category == planted wedge category) and scores the L2
ranking by precision@K = |topK ∩ positives| / K over the FULL-universe ranking.

What this certifies: L2 correctly translated L1's recovered category into account
prioritization — it pulled the planted high-value population to the top out of the
whole universe (pass = precision@K ≫ base rate). What it does NOT certify: the
ordering WITHIN the recovered block (segment-tier + under-penetration), which needs
true per-account value — Option B, deferred (spec §5.5). Stated, not implied away.

Attribution (spec §5.4): precision@K grades the COMPOSED L1→L2 decision — L2 ranks by
the card's recovered category, L3 scores against the manifest's true planted category.
On the reference world L1 recovers at precision/recall 1.0, so this isolates L2 in
practice, but the honest scope is the composed decision.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

from . import ground_truth as gt

# Fixed K sweep (spec §5.3). Reporting a sweep — not one convenient K — keeps the
# metric honest; K beyond the positive set (200) must degrade as a correctness check.
DEFAULT_KS = (10, 50, 100, 200)


def positive_set(manifest: dict, accounts_path) -> set:
    """The planted high-value population (spec §5.1): accounts whose observed Category
    equals the manifest's planted wedge category. The Category labels come from the
    OBSERVATION; only the planted-category identity comes from the answer key."""
    planted = gt.planted_category(manifest)
    acc = pd.read_csv(accounts_path, usecols=["AccountId", "Category"], dtype={"AccountId": str})
    return set(acc.loc[acc["Category"] == planted, "AccountId"])


def _ranked_ids(ranking: dict) -> list:
    rows = sorted(ranking["ranking"], key=lambda r: r["rank"])
    return [str(r["AccountId"]) for r in rows]


def precision_at_k(ranked_ids: list, positives: set, k: int) -> float:
    """|topK ∩ positives| / K. K is the size of the action shortlist (spec §5.3)."""
    if k <= 0:
        raise ValueError("K must be positive")
    topk = ranked_ids[:k]
    hits = sum(1 for a in topk if a in positives)
    return hits / k


def grade_ranking(manifest: dict, ranking: dict, accounts_path, ks=DEFAULT_KS) -> dict:
    """precision@K for one (manifest, L2 ranking) instance, plus the natural ceiling
    K=|positives| and the base rate the metric must beat."""
    positives = positive_set(manifest, accounts_path)
    ranked_ids = _ranked_ids(ranking)
    n = len(ranked_ids)
    n_pos = len(positives)
    out = {"n_accounts": n, "n_positives": n_pos,
           "base_rate": (n_pos / n) if n else None,
           "precision_at_k": {str(k): precision_at_k(ranked_ids, positives, k) for k in ks if k <= n}}
    # K = |positives|: at the positive-set size, precision and recall coincide (spec §5.3).
    if 0 < n_pos <= n:
        out["precision_at_n_positives"] = precision_at_k(ranked_ids, positives, n_pos)
    return out


def aggregate(records: list) -> dict:
    """Mean precision@K across a multi-seed set (spec §5.2). Each record is a
    grade_ranking() dict; only the FIXED Ks present in every record are averaged —
    those share one shortlist size across seeds, so the mean is well-defined."""
    if not records:
        return {"n": 0}
    ks = set(records[0]["precision_at_k"].keys())
    for r in records[1:]:
        ks &= set(r["precision_at_k"].keys())
    mean_pk = {k: round(statistics.fmean(r["precision_at_k"][k] for r in records), 6)
               for k in sorted(ks, key=int)}
    base_rates = [r["base_rate"] for r in records if r["base_rate"] is not None]
    base = round(statistics.fmean(base_rates), 6) if base_rates else None
    agg = {"n": len(records), "frame": "Option A (category membership)",
           "mean_base_rate": base, "mean_precision_at_k": mean_pk}
    # precision at K = |positives| is each seed's natural ceiling, but |positives|
    # varies by seed, so this mean mixes different K — report it transparently with
    # the K spread, never as a single-shortlist number (it would be misread otherwise).
    eqp = [(r["n_positives"], r["precision_at_n_positives"]) for r in records
           if "precision_at_n_positives" in r]
    if eqp:
        ks_used = sorted({k for k, _ in eqp})
        agg["precision_at_own_positive_ceiling"] = {
            "mean": round(statistics.fmean(p for _, p in eqp), 6),
            "k_varies_by_seed": len(ks_used) > 1,
            "k_range": [ks_used[0], ks_used[-1]],
            "note": "each seed measured at K = its own |positives| (precision=recall there); "
                    "the mean mixes K when k_varies_by_seed is true",
        }
    return agg


def load_ranking(ranking_path) -> dict:
    """Read a persisted L2 ranking artifact as a plain dict (consumed as data)."""
    return json.loads(Path(ranking_path).read_text())
