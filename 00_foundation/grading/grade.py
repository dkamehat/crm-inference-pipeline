"""
Aggregate grading over a SET of (manifest, card) pairs (L3-GRADING-SPEC §4, §7).

Grading is reported over a distribution of instances, never a single draw. Each
case is firewall-re-verified first; a failing card is rejected (never graded). The
2×2 marks TN as pending (no no-wedge profile in V1 — §4.3). Counts reconcile to the
total case count.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ground_truth, card_io, firewall, match, calibration


@dataclass
class Case:
    manifest_path: str
    card_path: str
    accounts_path: str
    opps_path: str
    label: str = ""          # optional human label for the instance


def grade_cases(cases: list[Case]) -> dict:
    counts = {"TP": 0, "FP": 0, "FN": 0}
    rejected = []
    mag_records = []
    per_case = []

    for case in cases:
        card = card_io.load_card(case.card_path)
        ok, reasons = firewall.reverify(card, case.accounts_path, case.opps_path)
        if not ok:
            rejected.append({"case": case.label or case.card_path, "reasons": reasons})
            per_case.append({"case": case.label or case.card_path, "status": "REJECTED",
                             "reasons": reasons})
            continue

        manifest = ground_truth.load(case.manifest_path)
        outcome = match.classify(manifest, card)
        counts[outcome] += 1
        entry = {"case": case.label or case.card_path, "status": outcome,
                 "segment": match.segment_crosscheck(manifest, card)}
        if outcome == "TP":
            mr = calibration.magnitude_record(manifest, card)
            mag_records.append(mr)
            entry["magnitude"] = mr
        per_case.append(entry)

    tp, fp, fn = counts["TP"], counts["FP"], counts["FN"]
    graded = tp + fp + fn
    n = len(cases)
    return {
        "n_cases": n,
        "graded": graded,
        "rejected": len(rejected),
        "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": "pending no-wedge profile"},
        "precision": (tp / (tp + fp)) if (tp + fp) else None,
        "recall": (tp / (tp + fn)) if (tp + fn) else None,
        "magnitude_calibration": calibration.aggregate_bias(mag_records),
        "firewall": {"graded": graded, "rejected": len(rejected), "rejections": rejected},
        "reconciliation_ok": (graded + len(rejected)) == n,
        "per_case": per_case,
    }
