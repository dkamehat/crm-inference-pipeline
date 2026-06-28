"""
Input contract for L2 decision (L2-DECISION-SPEC §3).

L2 reads exactly two things, both firewall-safe:
  accounts.csv      -> AccountId, Segment, Category   (the universe to rank)
  opportunities.csv -> AccountId, Stage               (won count = penetration)
plus the L1 recovery card (a persisted JSON, consumed as data — never re-running L1).

The ground-truth manifest is never touched (firewall, spec §2): L2 inherits L1's
manifest-non-reference. `observation_hash` is recomputed over the same two CSVs L1
hashed, so L3 can attest that L2 also saw only the observation (spec §6).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

# Observed realized-win label (same OBSERVED-schema convention L1 uses, not a manifest read).
WON_STAGE = "06 - Closed Won"

# The minimal observed fields L2 is allowed to consult (spec §3, §4.1). usecols keeps
# any other column (Amount, Source, LossReason, ...) out of the decision entirely.
_ACCOUNT_FIELDS = ["AccountId", "Segment", "Category"]
_OPP_FIELDS = ["AccountId", "Stage"]


def observation_hash(accounts_path, opps_path) -> str:
    """sha256 over the raw bytes of the two observed CSVs (path-sorted, stable).

    Defined identically to L1's hash (recovery.io / grading.provenance) so L3 can
    confirm L1 and L2 saw the same observation and neither read the answer."""
    h = hashlib.sha256()
    for p in sorted([str(accounts_path), str(opps_path)]):
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def load_accounts(accounts_path) -> pd.DataFrame:
    """The full account universe to rank (spec §3): AccountId, Segment, Category."""
    acc = pd.read_csv(accounts_path, usecols=_ACCOUNT_FIELDS, dtype={"AccountId": str})
    return acc.reset_index(drop=True)


def won_counts(opps_path, won_stage: str = WON_STAGE) -> dict:
    """Realized penetration per account = number of Closed-Won opportunities (spec §4.1).

    Won-only by design: Amount is populated on Won AND Lost opps, so a value-weighted
    count would conflate wins with losses — penetration must be realized wins only."""
    opp = pd.read_csv(opps_path, usecols=_OPP_FIELDS, dtype={"AccountId": str})
    won = opp[opp["Stage"] == won_stage]
    return won.groupby("AccountId").size().to_dict()


def recovered_category(card_path) -> str:
    """The category L1 recovered — the primary signal L2 acts on (spec §3, §4.1).

    Read from the card as data; L2 never imports or re-runs L1."""
    card = json.loads(Path(card_path).read_text())
    return str(card["recovered_wedge_category"]["category_id"])


# Same truth-leak guard L1 applies: no observed column name may betray a planted field.
_TRUTH_LIKE = re.compile(r"true|truth|plant|wedge|ground|latent|hidden|effect|mult|arpa|kappa",
                         re.IGNORECASE)


def audit_columns(accounts_path, opps_path) -> tuple[bool, list]:
    """No observed column name betrays a leaked truth field (spec §2 / firewall)."""
    cols = (list(pd.read_csv(accounts_path, nrows=0).columns)
            + list(pd.read_csv(opps_path, nrows=0).columns))
    hits = [c for c in cols if _TRUTH_LIKE.search(c)]
    return (len(hits) == 0), hits
