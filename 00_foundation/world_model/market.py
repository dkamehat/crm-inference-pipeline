"""
Market (hidden structures ② demand sources, ⑤ territory latent, ⑥ exogenous).

Holds the exogenous, regime-independent mechanics that shape arrival and outcome:
  - season_mult     : a smooth annual cycle plus a Q4 bump and a summer dip (⑥)
  - sample_*        : draw segment / category / territory / source from the profile
  - territory potential is skewed, and reps are spread evenly, which (combined with
    finite capacity in simulate) produces the coverage confound (⑤).
"""

from __future__ import annotations

import math
import random


class Market:
    def __init__(self, cfg, profile):
        self.cfg = cfg
        self.p = profile

    def season_mult(self, month_of_year: int) -> float:
        base = 1.0 + 0.18 * math.sin((month_of_year - 3) / 12 * 2 * math.pi)
        if month_of_year in (11, 12):
            base += 0.22
        if month_of_year in (7, 8):
            base -= 0.12
        return base

    def sample_segment(self, rng: random.Random) -> str:
        p = self.p
        return rng.choices(p.segments, weights=[p.seg_volume[s] for s in p.segments])[0]

    def sample_category(self, rng: random.Random) -> str:
        return rng.choice(self.p.categories)

    def sample_territory(self, rng: random.Random) -> str:
        p = self.p
        return rng.choices(p.territories, weights=[p.terr_potential[t] for t in p.territories])[0]

    def sample_source(self, rng: random.Random) -> str:
        return rng.choices(self.p.sources, weights=self.p.source_mix)[0]
