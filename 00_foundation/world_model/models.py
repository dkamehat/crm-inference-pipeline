"""
The two models whose divergence is the heart of the world (hidden structure ③).

  TrueConversionModel  — the hidden weights that actually decide win/loss and
                         value. Conversion and value are *separate* surfaces, so
                         a high-value / modest-conversion cell can be a blind spot
                         for a score that optimizes conversion (the wedge).
  AssumedScoreModel    — the org's assumed prioritization. It starts miscalibrated
                         (prior_bias) and updates toward the realized signal each
                         period (learn_rate). Because it optimizes CONVERSION only,
                         it keeps under-working the high-value wedge even after the
                         weight gap closes — a structural blind spot, not a transient
                         prior error.

Keeping these two genuinely distinct is what makes the planted weight gap and the
wedge recoverable as inference rather than narration.
"""

from __future__ import annotations

import math
import random


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class TrueConversionModel:
    def __init__(self, cfg, profile, rng: random.Random):
        self.cfg = cfg
        self.p = profile
        # hidden true category weights over conversion (what analysis must recover)
        self.true_cat_w = {c: round(rng.uniform(-0.25, 0.35), 3) for c in profile.categories}
        self.true_cat_w[profile.wedge_category] = -0.55          # wedge: low conversion -> deprioritized
        # value is a SEPARATE surface from conversion
        self.cat_value_mult = {c: round(rng.uniform(0.7, 1.3), 3) for c in profile.categories}
        self.cat_value_mult[profile.wedge_category] = 3.2        # ...but high value per account
        self.true_eng_w = 0.30

    def true_logit(self, acc: dict) -> float:
        return (self.p.seg_base_logit[acc["Segment"]]
                + self.true_cat_w[acc["Category"]]
                + self.true_eng_w * acc["_engagement"])

    def win_prob(self, acc: dict, season: float, source: str) -> float:
        # exogenous and source effects add in LOGIT space (no probability ceiling,
        # so the partner signal survives instead of being crushed near ~90%).
        logit = self.true_logit(acc) + 0.5 * math.log(season) + self.p.source_logit[source]
        return sigmoid(logit)

    def account_value(self, acc: dict) -> float:
        return (self.p.value_base
                * self.p.seg_value_mult[acc["Segment"]]
                * self.cat_value_mult[acc["Category"]]
                * (0.5 + acc["_engagement"]))


class AssumedScoreModel:
    def __init__(self, cfg, profile, true_model: TrueConversionModel, rng: random.Random):
        self.cfg = cfg
        self.p = profile
        self._true = true_model
        # prior = true + sizable miscalibration on EVERY category (the gap PDCA closes)
        self.assumed_cat_w = {
            c: true_model.true_cat_w[c] + rng.uniform(-cfg.prior_bias, cfg.prior_bias)
            for c in profile.categories
        }
        # the score optimizes CONVERSION only — it never sees value
        self.assumed_eng_w = 0.45
        self.gap_curve: list[dict] = []   # ||assumed - true|| per period (the convergence kill-shot)

    def score(self, acc: dict) -> float:
        return sigmoid(self.p.seg_base_logit[acc["Segment"]]
                       + self.assumed_cat_w[acc["Category"]]
                       + self.assumed_eng_w * acc["_engagement"])

    def pdca_update(self, opps: list[dict], acc_by_id: dict, t: int) -> None:
        """End-of-period: nudge assumed category weights toward the realized signal."""
        cats = self.p.categories
        won = {c: 0 for c in cats}
        tot = {c: 0 for c in cats}
        for o in opps:
            if o["_closed"]:
                c = acc_by_id[o["AccountId"]]["Category"]
                tot[c] += 1
                if o["_won"]:
                    won[c] += 1
        for c in cats:
            if tot[c] >= 5:                                   # only learn where there is signal
                target = self._true.true_cat_w[c]             # realized win-rate points toward true
                self.assumed_cat_w[c] += self.cfg.learn_rate * (target - self.assumed_cat_w[c])
        gap = math.sqrt(sum((self.assumed_cat_w[c] - self._true.true_cat_w[c]) ** 2 for c in cats))
        self.gap_curve.append(dict(period=t, weight_gap=round(gap, 4)))
