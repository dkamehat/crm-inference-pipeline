"""
RepBehaviorModel (hidden structure ④) — comp-driven record-layer distortion.

The true outcome of an opp is decided by the conversion model. What reps *record*
is a distorted projection of that truth, and the distortion is driven by comp
incentives, not randomness:

  - sandbag        : at quarter end, a recorded win is pushed into the next period
  - stage-lag      : an open opp is left at a stale stage (the rep doesn't update it),
                     so the recorded stage falls behind true progress
  - happy-ears     : an open opp is optimistically recorded one stage further along
  - close-optimism : the recorded close date is pulled earlier than the true close
  - attribution    : last-touch steals partner WINS into "inbound" (partner under-credited)

stage-lag and the days-open auto-close in simulate are complementary: the rep not
updating the stage is the *stale recorded stage*, while the cap keeps *days-open*
bounded — so a stuck opp looks neglected without ever becoming a 1,200-day impossibility.

Every method here touches only the *recorded* fields; the hidden truth is untouched,
which is exactly why the gap between them is recoverable.
"""

from __future__ import annotations

import random

from .config import MAX_OPEN_STAGE_IDX


class RepBehaviorModel:
    def __init__(self, cfg, profile):
        self.cfg = cfg
        self.p = profile

    def recorded_close_idx(self, t: int, won: bool, quarter_end: bool,
                           rng: random.Random, t_max: int) -> int:
        """Sandbag: at quarter end, push some recorded wins into the next period."""
        if quarter_end and won and rng.random() < self.cfg.sandbag_p:
            return min(t + 1, t_max)
        return t

    def close_optimism_offset(self, rng: random.Random) -> int:
        """Days the recorded close is pulled earlier than the true close (optimism)."""
        return rng.randint(0, self.cfg.close_optimism_days)

    def observed_source(self, true_src: str, won: bool, rng: random.Random) -> str:
        """Last-touch attribution: partner wins leak into 'inbound', under-crediting partner."""
        if true_src == "partner" and won and rng.random() < self.p.attrib_leak:
            return "inbound"
        return true_src

    def recorded_open_stage_idx(self, true_stage_idx: int, rng: random.Random) -> int:
        """Recorded stage for an OPEN opp, distorted by stage-lag then happy-ears.

        - stage-lag (stage_lag_p): the rep doesn't update the record, so it is held
          one stage *behind* true progress (a stale stage).
        - happy-ears (happy_p): otherwise, optimistically one stage *ahead* (capped).
        """
        if rng.random() < self.cfg.stage_lag_p:
            return max(1, true_stage_idx - 1)                  # stale: not updated
        if rng.random() < self.cfg.happy_p:
            return min(true_stage_idx + 1, MAX_OPEN_STAGE_IDX)  # optimistic
        return true_stage_idx
