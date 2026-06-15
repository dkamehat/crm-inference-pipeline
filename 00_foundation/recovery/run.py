"""
Entry point: observation -> recovery card (spec §5.6, §12).

    python -m recovery.run --data-dir ../world_model/data/v1
    python 00_foundation/recovery/run.py --out ./data/recovery_card.json

Reads ONLY accounts.csv + opportunities.csv (firewall, spec §2). Emits the card
and stops — it does NOT decide whether recovery succeeded (that is L3). The card
is git-ignored; regenerate it from the (also git-ignored) observation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from recovery import io, baseline as _bl, card as _card
    from recovery.wedge import recover
else:
    from . import io, baseline as _bl, card as _card
    from .wedge import recover

# Ratified defaults (spec §14 R1). N=8 categories ≥ S_min=6 in V1, so unchanged.
DEFAULTS = dict(s_min=6, alpha=0.05, n_perm=1000, p_low=0.5, j_min=0.8,
                k_kappa=1.0, n_bootstrap=200)


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "world_model" / "data" / "v1"


def _no_false_wedge_on_axis(acc_path, opp_path, axis: str, s_min: int,
                            alpha: float, seed: int) -> bool:
    """Negative control (spec §8.2): the existence gate must NOT fire on a
    non-planted axis (owner/region). Too few levels => cannot claim a wedge."""
    df = io.load_axis_frame(acc_path, opp_path, axis)
    if df["Axis"].nunique() < s_min:
        return True
    res = recover(df, category_col="Axis", segment_col="Segment",
                  alpha=alpha, n_perm=300, n_bootstrap=0, seed=seed)
    return not res.decision


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L1 wedge recovery -> card.")
    ap.add_argument("--data-dir", default=None, help="dir with accounts.csv + opportunities.csv")
    ap.add_argument("--accounts", default=None)
    ap.add_argument("--opps", default=None)
    ap.add_argument("--out", default=None, help="card output path (git-ignored)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir) if args.data_dir else _default_data_dir()
    acc_path = Path(args.accounts) if args.accounts else data_dir / "accounts.csv"
    opp_path = Path(args.opps) if args.opps else data_dir / "opportunities.csv"
    out_path = Path(args.out) if args.out else Path(__file__).resolve().parent / "data" / "recovery_card.json"

    d = DEFAULTS
    obs_hash = io.observation_hash(acc_path, opp_path)
    won = io.load_won(acc_path, opp_path)
    io.check_preconditions(won, d["s_min"])

    result = recover(won, alpha=d["alpha"], n_perm=d["n_perm"], p_low=d["p_low"],
                     j_min=d["j_min"], k_kappa=d["k_kappa"],
                     n_bootstrap=d["n_bootstrap"], seed=args.seed)
    bl = _bl.baseline_flags(won)
    no_truth_leak, _ = io.audit_columns(acc_path, opp_path)
    nfw = (_no_false_wedge_on_axis(acc_path, opp_path, "OwnerId", d["s_min"], d["alpha"], args.seed)
           and _no_false_wedge_on_axis(acc_path, opp_path, "Region", d["s_min"], d["alpha"], args.seed))

    card = _card.build_card(result, observation_hash=obs_hash, won_filter=io.WON_STAGE,
                            baseline=bl, no_truth_leak=no_truth_leak,
                            no_false_wedge_owner_region=nfw)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(card, indent=2))

    inv_ok = sum(1 for v in card["invariants"].values() if v)
    print(f"recovery card -> {out_path}")
    print(f"  observation_hash={obs_hash[:12]}...  manifest_read={card['provenance']['manifest_read']}")
    print(f"  n_won={result.n_won}  invariants={inv_ok}/5  members={len(result.members)}")
    print(f"  wedge_exists.decision={result.decision} (L1 claim; scoring is L3's job)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
