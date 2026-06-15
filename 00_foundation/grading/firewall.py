"""
Firewall re-verification (L3-GRADING-SPEC §4.4).

L3 audits the card's firewall claim instead of trusting it: recompute the
observation hash over the two observed CSVs and confirm it equals the card's, and
confirm `manifest_read == false`. A card that fails is REJECTED (not graded). This
keeps the "card as black box" posture while auditing the firewall from the answer
side.
"""

from __future__ import annotations

from . import provenance


def reverify(card: dict, accounts_path, opps_path) -> tuple[bool, list[str]]:
    """Return (ok, reasons). ok=False => the card must be rejected, never graded."""
    reasons: list[str] = []
    prov = card.get("provenance", {})

    if prov.get("manifest_read", True) is not False:
        reasons.append("manifest_read is not false")

    stored = prov.get("observation_hash")
    if not stored:
        reasons.append("missing observation_hash")
    else:
        recomputed = provenance.observation_hash(accounts_path, opps_path)
        if stored != recomputed:
            reasons.append("observation_hash mismatch (card vs recomputed)")

    return (len(reasons) == 0, reasons)
