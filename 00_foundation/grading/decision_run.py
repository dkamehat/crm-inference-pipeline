"""
Entry point: grade a SET of L2 rankings by precision@K and emit the report.

    python -m grading.decision_run --run-dir 00_foundation/harness/data/run

A run-dir holds one subdir per seed, each containing the answer manifest
(ground_truth.MANIFEST_NAME), the L2 ranking (decision_ranking.json), and accounts.csv.
These come from the multi-seed harness (which now runs L2 per seed, spec §5.2) —
L3 does not generate them. Each ranking is firewall-re-verified first; a ranking
that read the answer (or whose observation hash does not match) is rejected, not
graded (spec §6). With a single instance this runs as a smoke test and flags that
the aggregate needs the multi-seed set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from grading import ground_truth, firewall, decision
else:
    from . import ground_truth, firewall, decision

RANKING_NAME = "decision_ranking.json"


def _discover(run_dir: Path) -> list[Path]:
    out = []
    for d in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        m, r, a = d / ground_truth.MANIFEST_NAME, d / RANKING_NAME, d / "accounts.csv"
        o = d / "opportunities.csv"
        if all(p.exists() for p in (m, r, a, o)):
            out.append(d)
    return out


def grade_dirs(seed_dirs: list[Path]) -> dict:
    records, rejected, per_case = [], [], []
    for d in seed_dirs:
        ranking = decision.load_ranking(d / RANKING_NAME)
        ok, reasons = firewall.reverify(ranking, d / "accounts.csv", d / "opportunities.csv")
        if not ok:
            rejected.append({"case": d.name, "reasons": reasons})
            per_case.append({"case": d.name, "status": "REJECTED", "reasons": reasons})
            continue
        manifest = ground_truth.load(d / ground_truth.MANIFEST_NAME)
        rec = decision.grade_ranking(manifest, ranking, d / "accounts.csv")
        records.append(rec)
        per_case.append({"case": d.name, "status": "GRADED", **rec})
    return {
        "n_cases": len(seed_dirs),
        "graded": len(records),
        "rejected": len(rejected),
        "reconciliation_ok": (len(records) + len(rejected)) == len(seed_dirs),
        "aggregate": decision.aggregate(records),
        "firewall": {"graded": len(records), "rejected": len(rejected), "rejections": rejected},
        "per_case": per_case,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L3 decision-grading (precision@K) over L2 rankings.")
    ap.add_argument("--run-dir", required=True, help="dir of per-seed subdirs with L2 rankings")
    ap.add_argument("--out", default=None, help="report output path (git-ignored)")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir)
    seed_dirs = _discover(run_dir)
    if not seed_dirs:
        print(f"no (manifest, ranking, accounts) instances found under {run_dir} — "
              f"run `python -m harness.run` first (it now emits {RANKING_NAME} per seed)")
        return 2

    report = grade_dirs(seed_dirs)
    out_path = (Path(args.out) if args.out else
                Path(__file__).resolve().parent / "data" / "decision_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    agg = report["aggregate"]
    print(f"decision report -> {out_path}")
    print(f"  cases={report['n_cases']}  graded={report['graded']}  rejected={report['rejected']}  "
          f"reconciled={report['reconciliation_ok']}")
    if agg.get("n"):
        print(f"  base_rate≈{agg['mean_base_rate']}  mean precision@K={agg['mean_precision_at_k']}")
    if report["n_cases"] < 2:
        print("  [FLAG] single-instance smoke only — the aggregate (mean precision@K) "
              "needs a multi-seed set from `python -m harness.run --n 50`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
