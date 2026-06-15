"""
Recovery card assembly (spec §12). The card is the falsifiable artifact L3 scores
against the manifest. L1 fills `recovered_wedge_category` / `wedge_exists` (the
claims) and `absence_checks` / `invariants` / `baseline_parity` (its own,
answer-key-free health). `provenance.manifest_read=false` + `observation_hash` is
the firewall attestation. Schema keys match §12 exactly.
"""

from __future__ import annotations

from .wedge import RecoveryResult

SPEC = "L1-RECOVERY-SPEC"
SIGNAL = "06_wedge_value_concentration"


def build_card(result: RecoveryResult, *, observation_hash: str, won_filter: str,
               baseline: dict, no_truth_leak: bool,
               no_false_wedge_owner_region: bool) -> dict:
    agrees = bool(result.decision and result.category_id in baseline["categories"])
    return {
        "spec": SPEC,
        "signal": SIGNAL,
        "provenance": {
            "observation_hash": observation_hash,
            "manifest_read": False,
            "won_filter": won_filter,
            "value_field": result.value_field,
            "log_delta": result.log_delta,
            "permutation_B": result.n_perm,
            "alpha": result.alpha,
        },
        "wedge_exists": {
            "decision": result.decision,
            "separation_statistic": result.separation_statistic,
            "null_threshold": result.null_threshold,
            "p_value_vs_null": result.p_value_vs_null,
        },
        "recovered_wedge_category": {
            "category_id": result.category_id,
            "n_won": result.rec_n_won,
            "count_percentile": result.count_percentile,
            "raw_arpa": result.raw_arpa,
            "shrunk_effect_logspace": result.shrunk_effect_logspace,
            "elevation_ratio": result.elevation_ratio,
            "post_prob_elevated": result.post_prob_elevated,
            "cell_breakdown": result.cell_breakdown,
        },
        "absence_checks": {
            "no_wedge_in_high_count": result.absence_no_high_count,
            "no_wedge_in_low_arpa": result.absence_no_low_arpa,
            "no_fabrication_under_null": {
                "alpha": result.alpha,
                "observed_fpr": result.observed_fpr,
                "pass": bool(result.observed_fpr <= result.alpha + 0.05),
            },
            "no_truth_leak_in_observation": bool(no_truth_leak),
            "no_false_wedge_in_owner_region": bool(no_false_wedge_owner_region),
        },
        "baseline_parity": {
            "l0_rule_cells_flagged": baseline["cells"],
            "agrees_with_inference": agrees,
        },
        "invariants": {
            "INV_CVX": result.inv_cvx,
            "INV_MON": result.inv_mon,
            "INV_SCL": result.inv_scl,
            "INV_NULL": result.inv_null,
            "INV_STB": result.inv_stb,
        },
    }


# Exact key structure for schema-completeness tests (spec §12).
CARD_SCHEMA = {
    "spec": str, "signal": str,
    "provenance": {"observation_hash": str, "manifest_read": bool, "won_filter": str,
                   "value_field": str, "log_delta": float, "permutation_B": int, "alpha": float},
    "wedge_exists": {"decision": bool, "separation_statistic": float,
                     "null_threshold": float, "p_value_vs_null": float},
    "recovered_wedge_category": {"category_id": str, "n_won": int, "count_percentile": float,
                                 "raw_arpa": float, "shrunk_effect_logspace": float,
                                 "elevation_ratio": float, "post_prob_elevated": float,
                                 "cell_breakdown": list},
    "absence_checks": {"no_wedge_in_high_count": bool, "no_wedge_in_low_arpa": bool,
                       "no_fabrication_under_null": dict, "no_truth_leak_in_observation": bool,
                       "no_false_wedge_in_owner_region": bool},
    "baseline_parity": {"l0_rule_cells_flagged": list, "agrees_with_inference": bool},
    "invariants": {"INV_CVX": bool, "INV_MON": bool, "INV_SCL": bool,
                   "INV_NULL": bool, "INV_STB": bool},
}
