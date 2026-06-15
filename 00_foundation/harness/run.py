"""
Entry point: generate the multi-seed quad set the L3 grader consumes.

    python -m harness.run --n 50
    python -m harness.run --seeds 1000,1001,1002 --run-dir ./data/run

Then grade it:
    python -m grading.run --run-dir 00_foundation/harness/data/run

Generated quads are artifacts (git-ignored run-dir). The schedule is fixed and
reproducible; manifest.seed equals the schedule seed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from harness.generate import default_seeds, generate_set
else:
    from .generate import default_seeds, generate_set

_DEFAULT_RUN = Path(__file__).resolve().parent / "data" / "run"


def _parse_seeds(args) -> list[int]:
    if args.seeds:
        return [int(s) for s in args.seeds.split(",") if s.strip()]
    return default_seeds(args.n)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate multi-seed (manifest, card) quads.")
    ap.add_argument("--n", type=int, default=50, help="number of seeds (fixed schedule)")
    ap.add_argument("--seeds", default=None, help="explicit comma-separated seed list")
    ap.add_argument("--run-dir", default=None, help="output run-dir (git-ignored)")
    args = ap.parse_args(argv)

    seeds = _parse_seeds(args)
    run_dir = Path(args.run_dir) if args.run_dir else _DEFAULT_RUN
    print(f"generating {len(seeds)} quads -> {run_dir}")
    dirs = generate_set(seeds, run_dir)
    print(f"done: {len(dirs)} seed dirs under {run_dir}")
    print(f"grade with:  python -m grading.run --run-dir {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
