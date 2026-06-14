"""
ControllingEntityGraph (hidden structure ①).

A minority of accounts are owned by controlling entities whose sizes follow a
power law with a heavy-tail cap: a few entities own many accounts, most own one
or two. The true parentage lives only in the ground-truth manifest; the observed
CRM hides or mis-parents a configurable fraction of the links, so the recorded
account table looks like a flat list of independent accounts.

This is what lets analysis recover "the true number of distinct buyers is far
below the CRM row count, and a few entities concentrate ownership."
"""

from __future__ import annotations

import random

import numpy as np


class ControllingEntityGraph:
    def __init__(self, cfg):
        self.cfg = cfg
        self.assignments: list[str] = []   # controlling-entity id per controlled slot ("" beyond)

    def build(self, np_rng: "np.random.Generator", rng: random.Random) -> "ControllingEntityGraph":
        cfg = self.cfg
        n_controlled = int(cfg.n_accounts * cfg.ctrl_share)

        sizes: list[tuple[str, int]] = []
        remaining, eid = n_controlled, 0
        while remaining > 0:
            size = max(1, int(np_rng.pareto(cfg.ctrl_alpha)) + 1)
            size = min(size, remaining, cfg.ctrl_entity_cap)   # heavy tail, but capped
            sizes.append((f"CE{eid:04d}", size))
            remaining -= size
            eid += 1

        assign: list[str] = []
        for ce_id, size in sizes:
            assign.extend([ce_id] * size)
        rng.shuffle(assign)
        self.assignments = assign
        return self

    def ce_for_index(self, i: int) -> str:
        """True controlling entity for account slot ``i`` ("" if independent)."""
        return self.assignments[i] if i < len(self.assignments) else ""

    def observed_ce(self, true_ce: str, rng: random.Random) -> str:
        """Project the true link onto the observed CRM: hidden/mis-parented a fraction of the time."""
        if true_ce and rng.random() < self.cfg.hidden_parent_rate:
            return ""    # hidden in the observed CRM
        return true_ce
