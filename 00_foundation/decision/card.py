"""
L2 decision artifact (L2-DECISION-SPEC §3 output contract).

The ranking is the falsifiable artifact L3 decision-grading scores against the
manifest's planted population (precision@K). `provenance.manifest_read=false` +
`observation_hash` is the firewall attestation L3 re-verifies (spec §6); the
attestation is byte-identical in form to L1's so one verifier audits both layers.
`no_truth_leak_in_observation` mirrors L1's self-attestation (a truth-like column
in the observation would void the firewall) — recorded here, not only in L1.
"""

from __future__ import annotations

from .rank import RankedAccount

SPEC = "L2-DECISION-SPEC"


def build_ranking(ranked: list[RankedAccount], *, observation_hash: str,
                  recovered_category: str, weights: tuple[float, float, float],
                  no_truth_leak: bool) -> dict:
    return {
        "spec": SPEC,
        "provenance": {
            "observation_hash": observation_hash,
            "manifest_read": False,
            "no_truth_leak_in_observation": bool(no_truth_leak),
            "recovered_category": recovered_category,
            "weights": {"W1": weights[0], "W2": weights[1], "W3": weights[2]},
            "n_accounts": len(ranked),
        },
        "ranking": [
            {
                "AccountId": r.account_id,
                "rank": r.rank,
                "score": r.score,
                "in_recovered_category": r.in_recovered_category,
                "segment_tier": r.segment_tier,
                "n_won": r.n_won,
            }
            for r in ranked
        ],
    }


# Exact key structure for schema-completeness tests (spec §3 output contract).
RANKING_SCHEMA = {
    "spec": str,
    "provenance": {"observation_hash": str, "manifest_read": bool,
                   "no_truth_leak_in_observation": bool, "recovered_category": str,
                   "weights": dict, "n_accounts": int},
    "ranking": list,
}
ROW_SCHEMA = {"AccountId": str, "rank": int, "score": float, "in_recovered_category": bool,
              "segment_tier": int, "n_won": int}
