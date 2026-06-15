"""
Calibration probe (orchestration lane) — measures the recovery existence gate's
false-positive rate and power over synthetic instances, reproducing the README's
headline FPR / power figures with a committed, runnable computation.

It invents no methodology: it calls the committed `recovery.wedge.recover` (whose
permutation-null gate decides existence) over synthetic multiplicative instances.
For the null it permutes the category labels (Amount ⊥ category); for power it
plants a category at a given value multiplier. No manifest is involved (recovery
receives only the synthetic observation), so the firewall is preserved trivially.

Defaults reproduce the original probe exactly (fixed seeds):
  FPR   = decision-rate over 120 null instances        (seeds 0..119)
  power = decision-rate over 40 planted instances each  (3.2x seeds 1000.., 1.8x seeds 2000..)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_FOUNDATION = Path(__file__).resolve().parent.parent
if str(_FOUNDATION) not in sys.path:
    sys.path.insert(0, str(_FOUNDATION))

from recovery.wedge import recover

WON_STAGE = "06 - Closed Won"
_SEGMENTS = ["S1", "S2", "S3"]
_SEG_MIX = [0.62, 0.30, 0.08]
_SEG_MULT = {"S1": 0.4, "S2": 1.0, "S3": 2.6}
_N_CAT = 8
_WEDGE_CAT = "C3"
_VALUE_BASE = 8000.0


def synth_instance(seed: int, n: int = 900, wedge_mult: float = 3.2, null: bool = False) -> pd.DataFrame:
    """Synthetic multiplicative won-instance: Amount = base·seg·cat·(0.5+eng), with one
    rare category at `wedge_mult`. null=True permutes category to break Amount⊥category."""
    r = np.random.default_rng(seed)
    cats = [f"C{i}" for i in range(_N_CAT)]
    cat_mult = {c: float(r.uniform(0.7, 1.3)) for c in cats}
    cat_mult[_WEDGE_CAT] = wedge_mult
    p = np.ones(_N_CAT)
    p[cats.index(_WEDGE_CAT)] = 0.12                       # rare wedge category
    p = p / p.sum()
    seg = r.choice(_SEGMENTS, n, p=_SEG_MIX)
    cat = r.choice(cats, n, p=p)
    eng = r.random(n)
    amt = np.round(_VALUE_BASE * np.array([_SEG_MULT[s] for s in seg])
                   * np.array([cat_mult[c] for c in cat]) * (0.5 + eng), -2)
    df = pd.DataFrame({"OppId": range(n), "AccountId": range(n), "Stage": WON_STAGE,
                       "Amount": amt, "Segment": seg, "Category": cat})
    if null:
        df["Category"] = r.permutation(df["Category"].to_numpy())
    return df


def false_positive_rate(n_instances: int = 120, n_perm: int = 300, alpha: float = 0.05) -> dict:
    """Empirical FPR: fraction of NULL instances where the existence gate fires (≈ alpha)."""
    fires = sum(recover(synth_instance(s, null=True), n_perm=n_perm, n_bootstrap=0,
                        alpha=alpha, seed=s).decision for s in range(n_instances))
    return {"n_instances": n_instances, "fires": int(fires), "fpr": fires / n_instances,
            "alpha": alpha, "n_perm": n_perm}


def power(effect: float, n_instances: int = 40, n_perm: int = 300, alpha: float = 0.05,
          seed_base: int = 0) -> dict:
    """Detection power: fraction of PLANTED instances (wedge at `effect`) where the gate fires."""
    fires = sum(recover(synth_instance(seed_base + s, wedge_mult=effect), n_perm=n_perm,
                        n_bootstrap=0, alpha=alpha, seed=s).decision for s in range(n_instances))
    return {"effect": effect, "n_instances": n_instances, "fires": int(fires),
            "power": fires / n_instances, "seed_base": seed_base}


def run_probe(n_fpr: int = 120, n_power: int = 40, n_perm: int = 300, alpha: float = 0.05) -> dict:
    """Full FPR + power@{3.2x, 1.8x} report (defaults reproduce the README figures)."""
    return {
        "alpha": alpha, "n_perm": n_perm,
        "false_positive_rate": false_positive_rate(n_fpr, n_perm, alpha),
        "power": [
            power(3.2, n_power, n_perm, alpha, seed_base=1000),
            power(1.8, n_power, n_perm, alpha, seed_base=2000),
        ],
    }
