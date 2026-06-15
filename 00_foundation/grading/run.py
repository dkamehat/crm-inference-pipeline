"""
Entry point: grade a SET of (manifest, card) pairs and emit the report.

    python -m grading.run --run-dir <dir-of-per-seed-subdirs>
    python -m grading.run            # smoke: grade the single available sample pair

A run-dir holds one subdir per instance, each containing the answer manifest
(ground_truth.MANIFEST_NAME), recovery_card.json, accounts.csv, opportunities.csv.
L3 does NOT generate these
(that needs L1) — they come from an L1/orchestration-lane multi-seed harness. With
only the single sample pair, this runs as a smoke test and flags that the aggregate
needs the multi-seed set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from grading import ground_truth
    from grading.grade import Case, grade_cases
else:
    from . import ground_truth
    from .grade import Case, grade_cases

_FOUNDATION = Path(__file__).resolve().parent.parent


def _smoke_case() -> Case:
    v1 = _FOUNDATION / "world_model" / "data" / "v1"
    return Case(
        manifest_path=str(v1 / ground_truth.MANIFEST_NAME),
        card_path=str(_FOUNDATION / "recovery" / "data" / "recovery_card.json"),
        accounts_path=str(v1 / "accounts.csv"),
        opps_path=str(v1 / "opportunities.csv"),
        label="v1-seed42-smoke",
    )


def _discover(run_dir: Path) -> list[Case]:
    cases = []
    for d in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        m, c = d / ground_truth.MANIFEST_NAME, d / "recovery_card.json"
        a, o = d / "accounts.csv", d / "opportunities.csv"
        if all(p.exists() for p in (m, c, a, o)):
            cases.append(Case(str(m), str(c), str(a), str(o), label=d.name))
    return cases


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L3 grading over (manifest, card) pairs.")
    ap.add_argument("--run-dir", default=None, help="dir of per-instance subdirs")
    ap.add_argument("--out", default=None, help="report output path (git-ignored)")
    args = ap.parse_args(argv)

    if args.run_dir:
        cases = _discover(Path(args.run_dir))
        if not cases:
            print(f"no (manifest, card) pairs found under {args.run_dir}")
            return 2
    else:
        smoke = _smoke_case()
        if not all(Path(p).exists() for p in
                   (smoke.manifest_path, smoke.card_path, smoke.accounts_path, smoke.opps_path)):
            print("smoke pair incomplete; provide --run-dir with persisted (manifest, card) pairs")
            return 2
        cases = [smoke]

    report = grade_cases(cases)

    out_path = Path(args.out) if args.out else _FOUNDATION / "grading" / "data" / "grading_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    c = report["confusion"]
    print(f"grading report -> {out_path}")
    print(f"  cases={report['n_cases']}  graded={report['graded']}  rejected={report['rejected']}  "
          f"reconciled={report['reconciliation_ok']}")
    print(f"  confusion: TP={c['TP']} FP={c['FP']} FN={c['FN']} TN={c['TN']}")
    print(f"  precision={report['precision']}  recall={report['recall']}")
    print(f"  magnitude_calibration={report['magnitude_calibration']}")
    if report["n_cases"] < 2:
        print("  [FLAG] single-instance smoke only — the aggregate (precision/recall, "
              "bias dispersion) needs a multi-seed (manifest, card) set from an "
              "L1/orchestration-lane harness, not L3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
