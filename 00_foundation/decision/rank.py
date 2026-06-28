"""
The L2 ranker (L2-DECISION-SPEC §4): rank the FULL account universe so a sales team
knows which accounts to work next.

Lexicographic by construction — three keys, in strict priority order:
  1. in_recovered_category  (pursue the category L1 recovered) — dominates everything
  2. segment_tier           (observable value proxy: Enterprise > MidMarket > SMB)
  3. under-penetration       (fewer Closed-Won first: "high value, still not worked")

The weights only need to preserve key priority (W1 >> W2·max_tier >> W3·max(1/(1+n_won))),
not be calibrated — so there is no tuning sensitivity (spec §4.2). Ties break
deterministically by AccountId. L2 reads observations + the L1 card only; it never
reads the answer and it does not score true monetary value (spec §4.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Observable value proxy. Order matches the design intent seg_value_mult
# (SMB 0.4 < MidMarket 1.0 < Enterprise 2.6) — an OBSERVABLE assumption on the label
# order, not a manifest read (spec §4.1 ⚠). Unknown labels tier 0 (ranked last).
SEGMENT_TIER = {"Enterprise": 3, "MidMarket": 2, "SMB": 1}

# Lexicographic weights (spec §4.2). Any W1 >> W2·max_tier >> W3 works; these are an
# implementation detail — the spec fixes only key priority + determinism.
W1, W2, W3 = 1000.0, 10.0, 1.0


@dataclass(frozen=True)
class RankedAccount:
    account_id: str
    rank: int
    score: float
    in_recovered_category: bool
    segment_tier: int
    n_won: int


def _segment_tier(segment) -> int:
    return SEGMENT_TIER.get(str(segment), 0)


def rank_accounts(accounts: pd.DataFrame, won_by_account: dict, recovered_category: str,
                  *, weights: tuple[float, float, float] = (W1, W2, W3)) -> list[RankedAccount]:
    """Rank every account in `accounts` (spec §3 — full universe, never pre-filtered).

    accounts: DataFrame with AccountId, Segment, Category.
    won_by_account: {AccountId -> Closed-Won count} (missing => 0).
    recovered_category: the category id from the L1 card.
    Returns the ranking sorted best-first (rank 1 = work this account first)."""
    w1, w2, w3 = weights
    rows = []
    for acc_id, segment, category in zip(
            accounts["AccountId"].astype(str), accounts["Segment"], accounts["Category"]):
        in_cat = (str(category) == recovered_category)
        tier = _segment_tier(segment)
        n_won = int(won_by_account.get(acc_id, 0))
        score = w1 * (1.0 if in_cat else 0.0) + w2 * tier + w3 * (1.0 / (1.0 + n_won))
        rows.append((acc_id, score, in_cat, tier, n_won))

    # Best-first: score descending, AccountId ascending as the deterministic tie-break.
    rows.sort(key=lambda r: (-r[1], r[0]))
    return [RankedAccount(account_id=r[0], rank=i + 1, score=round(r[1], 6),
                          in_recovered_category=r[2], segment_tier=r[3], n_won=r[4])
            for i, r in enumerate(rows)]
