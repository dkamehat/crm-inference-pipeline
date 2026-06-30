"""
Entry point: (observation + L1 card) -> ranked account list (L2-DECISION-SPEC §3).

    python -m decision.run --data-dir ../world_model/data/v1 --card ../recovery/data/recovery_card.json
    python 00_foundation/decision/run.py --out ./data/decision_ranking.json

Reads ONLY accounts.csv + opportunities.csv + the L1 card (firewall, spec §2). Emits
the ranking and stops — it does NOT decide whether the ranking was good (that is L3's
precision@K). The ranking is git-ignored; regenerate it from the (also git-ignored)
observation + card.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from decision import io, card as _card
    from decision.rank import rank_accounts, W1, W2, W3
else:
    from . import io, card as _card
    from .rank import rank_accounts, W1, W2, W3


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "world_model" / "data" / "v1"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L2 account-prioritization ranking -> artifact.")
    ap.add_argument("--data-dir", default=None, help="dir with accounts.csv + opportunities.csv")
    ap.add_argument("--accounts", default=None)
    ap.add_argument("--opps", default=None)
    ap.add_argument("--card", default=None, help="L1 recovery card (recovered category)")
    ap.add_argument("--out", default=None, help="ranking output path (git-ignored)")
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir) if args.data_dir else _default_data_dir()
    acc_path = Path(args.accounts) if args.accounts else data_dir / "accounts.csv"
    opp_path = Path(args.opps) if args.opps else data_dir / "opportunities.csv"
    card_path = (Path(args.card) if args.card else
                 Path(__file__).resolve().parent.parent / "recovery" / "data" / "recovery_card.json")
    out_path = (Path(args.out) if args.out else
                Path(__file__).resolve().parent / "data" / "decision_ranking.json")

    obs_hash = io.observation_hash(acc_path, opp_path)
    no_truth_leak, _ = io.audit_columns(acc_path, opp_path)
    accounts = io.load_accounts(acc_path)
    won_by_account = io.won_counts(opp_path)
    rec_cat = io.recovered_category(card_path)

    ranked = rank_accounts(accounts, won_by_account, rec_cat)
    weights = (W1, W2, W3)
    ranking = _card.build_ranking(ranked, observation_hash=obs_hash,
                                  recovered_category=rec_cat, weights=weights,
                                  no_truth_leak=no_truth_leak)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ranking, indent=2))

    n_cat = sum(1 for r in ranked if r.in_recovered_category)
    top = ranked[0]
    print(f"decision ranking -> {out_path}")
    print(f"  observation_hash={obs_hash[:12]}...  manifest_read={ranking['provenance']['manifest_read']}"
          f"  no_truth_leak={no_truth_leak}")
    print(f"  recovered_category={rec_cat}  accounts={len(ranked)}  in_category={n_cat}")
    print(f"  rank#1: {top.account_id} (tier={top.segment_tier}, n_won={top.n_won})")
    print(f"  precision@K vs ground truth is L3's job, not L2's")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
