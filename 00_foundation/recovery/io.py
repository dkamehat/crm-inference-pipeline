"""
Input contract for L1 recovery (spec §3).

Reads ONLY the minimal observed fields the wedge signal needs:
  accounts.csv      -> AccountId, Segment, Category
  opportunities.csv -> OppId, AccountId, Stage, Amount

Everything else (usage/health/activities/users/assumed_scores) is irrelevant to
the wedge and is not read. The ground-truth manifest is never touched (firewall,
spec §2). `observation_hash` lets L3 independently attest that L1 saw only the
observation.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

# Observed stage label for a realized win. This is an OBSERVED-schema convention
# (the value-blind-spot lives in realized value), not a manifest read. Matches the
# L0 self_check won filter (spec §3.2).
WON_STAGE = "06 - Closed Won"

# Fields L1 is allowed to consult for the wedge (spec §3.1). Reading via usecols
# enforces the minimal contract and keeps any stray columns out of the analysis.
_ACCOUNT_FIELDS = ["AccountId", "Segment", "Category"]
_OPP_FIELDS = ["OppId", "AccountId", "Stage", "Amount"]


def observation_hash(accounts_path, opps_path) -> str:
    """sha256 over the raw bytes of the two observed CSVs (path-sorted, stable).

    Stamped into the card so L3 can recompute it and confirm L1 touched only the
    observation (spec §2.3, INV-ATT)."""
    h = hashlib.sha256()
    for p in sorted([str(accounts_path), str(opps_path)]):
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def load_won(accounts_path, opps_path, won_stage: str = WON_STAGE) -> pd.DataFrame:
    """Won opportunities mapped to their (Segment, Category) cell (spec §3.2).

    Granularity is the transaction (won opp), not the account — the same basis L0
    used for ARPA (spec §3.2 / R3); account-dedup is a robustness variant (B-L1-5).
    """
    acc = pd.read_csv(accounts_path, usecols=_ACCOUNT_FIELDS)
    opp = pd.read_csv(opps_path, usecols=_OPP_FIELDS)
    won = opp[opp["Stage"] == won_stage].merge(acc, on="AccountId", how="left")
    return won.reset_index(drop=True)


def check_preconditions(won: pd.DataFrame, s_min: int) -> dict:
    """Fail-fast preconditions (spec §3.3). Returns a small record for the card."""
    n_categories = int(won["Category"].nunique())
    if n_categories < s_min:
        raise ValueError(
            f"n_categories={n_categories} < S_min={s_min}: permutation null unstable (spec §3.3, §7.4)")
    if not (won["Amount"] > 0).all():
        raise ValueError("non-positive Amount present; log-scale unsafe (spec §3.3)")
    if won.empty:
        raise ValueError("no won opportunities in observation")
    return {"n_categories": n_categories, "n_won": int(len(won)),
            "amount_min": float(won["Amount"].min())}


# Columns whose name would betray that a truth/plant value leaked into the
# observation (spec §8.2 "no truth leak"). The observed schema has none of these.
_TRUTH_LIKE = re.compile(r"true|truth|plant|wedge|ground|latent|hidden|effect|mult|arpa|kappa",
                         re.IGNORECASE)


def audit_columns(accounts_path, opps_path) -> tuple[bool, list]:
    """No observed column name betrays a leaked truth field (spec §8.2)."""
    cols = (list(pd.read_csv(accounts_path, nrows=0).columns)
            + list(pd.read_csv(opps_path, nrows=0).columns))
    hits = [c for c in cols if _TRUTH_LIKE.search(c)]
    return (len(hits) == 0), hits


def load_axis_frame(accounts_path, opps_path, axis: str, won_stage: str = WON_STAGE) -> pd.DataFrame:
    """Won frame for a NON-planted control axis (owner or region) — used only by the
    §8.2 negative control (no false wedge off the value axis). The axis column is
    returned as 'Axis'; Segment is kept as the adjuster."""
    if axis == "OwnerId":
        acc = pd.read_csv(accounts_path, usecols=["AccountId", "Segment"])
        opp = pd.read_csv(opps_path, usecols=["OppId", "AccountId", "Stage", "Amount", "OwnerId"])
        won = opp[opp["Stage"] == won_stage].merge(acc, on="AccountId", how="left")
        return won.rename(columns={"OwnerId": "Axis"}).reset_index(drop=True)
    if axis == "Region":
        acc = pd.read_csv(accounts_path, usecols=["AccountId", "Segment", "Region"])
        opp = pd.read_csv(opps_path, usecols=["OppId", "AccountId", "Stage", "Amount"])
        won = opp[opp["Stage"] == won_stage].merge(acc, on="AccountId", how="left")
        return won.rename(columns={"Region": "Axis"}).reset_index(drop=True)
    raise ValueError(f"unknown control axis: {axis}")
