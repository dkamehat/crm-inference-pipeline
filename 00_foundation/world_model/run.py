"""
Entry point: generate the observed CSVs + ground-truth manifest, then print the
planted-signal recovery report.

    python -m world_model.run --seed 42 --periods 18
    python 00_foundation/world_model/run.py --seed 7 --out ./data/v1

Output defaults to ``<package>/data/<profile>/`` so the generator and its data
travel together; data is reproducible from the seed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

# Support both `python -m world_model.run` and `python run.py`.
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from world_model.config import Config, PROFILES
    from world_model.simulate import WorldModel
    from world_model.self_check import self_check
else:
    from .config import Config, PROFILES
    from .simulate import WorldModel
    from .self_check import self_check


def _default_out(profile_name: str) -> Path:
    return Path(__file__).resolve().parent / "data" / profile_name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L0 WorldModel generator (thin slice).")
    ap.add_argument("--seed", type=int, default=None, help="override Config.seed")
    ap.add_argument("--periods", type=int, default=None, help="override Config.t_periods")
    ap.add_argument("--accounts", type=int, default=None, help="override Config.n_accounts")
    ap.add_argument("--profile", default="v1", choices=sorted(PROFILES), help="world profile")
    ap.add_argument("--out", default=None, help="output directory (default: <package>/data/<profile>)")
    args = ap.parse_args(argv)

    profile = PROFILES[args.profile]
    cfg = Config()
    if args.seed is not None:
        cfg.seed = args.seed
    if args.periods is not None:
        cfg.t_periods = args.periods
    if args.accounts is not None:
        cfg.n_accounts = args.accounts

    out = Path(args.out) if args.out else _default_out(profile.name)

    wm = WorldModel(cfg, profile).simulate()
    wm.emit(out)

    print(f"emitted profile '{profile.name}' (seed={cfg.seed}, periods={cfg.t_periods}) to: {out}")
    for f in sorted(Path(out).glob("*")):
        print("  ", f.name)
    self_check(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
