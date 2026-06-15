"""
Entry point: run the calibration probe and emit the FPR / power report.

    python -m harness.probe_run

Reproduces the README's headline detection figures with one command. The report
is an artifact (git-ignored); only source + tests are committed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from harness.calibration import run_probe
else:
    from .calibration import run_probe

_DEFAULT_OUT = Path(__file__).resolve().parent / "data" / "calibration_report.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Recovery calibration probe (FPR + power).")
    ap.add_argument("--n-fpr", type=int, default=120)
    ap.add_argument("--n-power", type=int, default=40)
    ap.add_argument("--n-perm", type=int, default=300)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--out", default=None, help="report path (git-ignored)")
    args = ap.parse_args(argv)

    report = run_probe(n_fpr=args.n_fpr, n_power=args.n_power, n_perm=args.n_perm, alpha=args.alpha)
    out = Path(args.out) if args.out else _DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    fpr = report["false_positive_rate"]
    print(f"calibration report -> {out}")
    print(f"  FPR = {fpr['fires']}/{fpr['n_instances']} = {fpr['fpr']:.3f}  (target alpha={fpr['alpha']})")
    for p in report["power"]:
        print(f"  power @{p['effect']}x = {p['fires']}/{p['n_instances']} = {p['power']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
