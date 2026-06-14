"""
WorldModel — the period loop that ties the hidden structures together (spec §3).

Each period runs the causal loop:
  1. exogenous   : seasonality multiplier for the month
  2. demand      : (opps were spawned up front with created >= account.created)
  3. priority    : the org scores OPEN opps with the ASSUMED model and works the
                   top of the list under finite per-territory / global capacity
  4. outcome     : worked opps win/lose by the TRUE model (logit-space season +
                   source lift); loss reasons are segment-conditional
  5. distortion  : RepBehaviorModel skews the recorded close/source/stage
  6. activation  : (built after the loop) won accounts penetrate ~ true value
  7. learning    : the assumed model updates toward the realized signal (PDCA)
  8. emit        : handled by emit.py

An explicit days-open cap auto-closes the pathological tail so no opp can sit open
forever; in the thin slice the bounded window keeps everything well under it.
"""

from __future__ import annotations

import math
import random

import numpy as np

from .config import Config, V1_PROFILE, STAGES, WON_STAGE, LOST_STAGE, TERMINAL_STAGES
from .graph import ControllingEntityGraph
from .market import Market
from .models import TrueConversionModel, AssumedScoreModel
from .reps import RepBehaviorModel
from .timeutil import month_index_to_date, date_minus


class WorldModel:
    def __init__(self, cfg: Config | None = None, profile=None):
        self.cfg = cfg or Config()
        self.p = profile or V1_PROFILE
        self.rng = random.Random(self.cfg.seed)
        self.np = np.random.default_rng(self.cfg.seed)

        # component models (order of rng consumption is fixed for reproducibility)
        self.true = TrueConversionModel(self.cfg, self.p, self.rng)
        self.assumed = AssumedScoreModel(self.cfg, self.p, self.true, self.rng)
        self.reps = RepBehaviorModel(self.cfg, self.p)
        self.market = Market(self.cfg, self.p)
        self.graph = ControllingEntityGraph(self.cfg)

        self.accounts: list[dict] = []
        self.acc_by_id: dict[str, dict] = {}
        self.opps: list[dict] = []
        self.users: list[dict] = []
        self.activities: list[dict] = []
        self.usage: list[dict] = []
        self.health: list[dict] = []
        self.coverage_log: list[dict] = []

    # ----- population ------------------------------------------------------ #
    def _build_accounts(self) -> None:
        cfg, p = self.cfg, self.p
        self.graph.build(self.np, self.rng)
        win_days = 365 * 2   # accounts created in a window BEFORE the sim window (so cohorts exist)

        accounts = []
        for i in range(cfg.n_accounts):
            seg = self.market.sample_segment(self.rng)
            cat = self.market.sample_category(self.rng)
            terr = self.market.sample_territory(self.rng)
            eng = self.rng.random()
            created_offset = self.rng.randint(0, win_days)
            created = date_minus(cfg.start_year, cfg.start_month, win_days - created_offset)
            ce = self.graph.ce_for_index(i)
            accounts.append(dict(
                AccountId=f"A{i + 1:05d}", AccountName=f"Account-{i + 1:05d}",
                Segment=seg, Category=cat, Territory=terr,
                _engagement=eng, CreatedDate=created, _true_ce=ce,
            ))
        self.accounts = accounts
        self.acc_by_id = {a["AccountId"]: a for a in accounts}

    def _build_users(self) -> None:
        cfg, p = self.cfg, self.p
        users = []
        # SMB reps spread roughly EVENLY across territories -> coverage confound vs. potential
        for i in range(cfg.n_reps_smb):
            users.append(dict(OwnerId=f"U{i + 1:03d}", OwnerName=f"Rep-{i + 1:03d}",
                              Motion="SMB", Region=p.territories[i % len(p.territories)]))
        for j in range(cfg.n_reps_named):
            k = cfg.n_reps_smb + j
            users.append(dict(OwnerId=f"U{k + 1:03d}", OwnerName=f"Rep-{k + 1:03d}",
                              Motion="Named", Region="GLOBAL"))
        self.users = users
        self.smb_reps_by_terr = {t: [u for u in users if u["Motion"] == "SMB" and u["Region"] == t]
                                 for t in p.territories}
        self.named_reps = [u for u in users if u["Motion"] == "Named"]

    def _spawn_opps(self) -> None:
        cfg = self.cfg
        opps = []
        oid = 0
        for acc in self.accounts:
            n_opp = self.rng.choices([1, 2, 3], weights=[0.55, 0.32, 0.13])[0]
            for _ in range(n_opp):
                oid += 1
                created_idx = self.rng.randint(0, cfg.t_periods - 1)
                created = month_index_to_date(cfg.start_year, cfg.start_month, created_idx)
                if created < acc["CreatedDate"]:                 # enforce opp.created >= account.created
                    created = acc["CreatedDate"][:7] + "-01"
                src_true = self.market.sample_source(self.rng)
                opps.append(dict(
                    OppId=f"O{oid:06d}", AccountId=acc["AccountId"],
                    _created_idx=created_idx, CreatedDate=created,
                    _src_true=src_true, _true_stage_idx=0, Stage=STAGES[0],
                    _closed=False, _won=None, _true_close_idx=None, _rec_close_idx=None,
                    CloseDate="", Amount=0.0, LossReason="", OwnerId="", Source="",
                ))
        self.opps = opps
        self._opps_by_terr_motion = {}
        for o in opps:
            acc = self.acc_by_id[o["AccountId"]]
            key = (acc["Territory"], "Named" if acc["_true_ce"] else "SMB")
            self._opps_by_terr_motion.setdefault(key, []).append(o)

    # ----- simulation ------------------------------------------------------ #
    def simulate(self) -> "WorldModel":
        cfg, p = self.cfg, self.p
        self._build_accounts()
        self._build_users()
        self._spawn_opps()

        cap_months = max(1, round(cfg.stage_lag_cap_days / 30))

        for t in range(cfg.t_periods):
            month_date = month_index_to_date(cfg.start_year, cfg.start_month, t)
            moy = int(month_date[5:7])
            season = self.market.season_mult(moy)
            quarter_end = moy in (3, 6, 9, 12)

            self._auto_close_stale(t, cap_months)

            # --- SMB motion: per territory, capacity-limited, prioritized by ASSUMED score ---
            for terr in p.territories:
                cap = len(self.smb_reps_by_terr[terr]) * cfg.rep_cap
                cands = [o for o in self._opps_by_terr_motion.get((terr, "SMB"), [])
                         if (not o["_closed"]) and o["_created_idx"] <= t]
                cands.sort(key=lambda o: self.assumed.score(self.acc_by_id[o["AccountId"]]), reverse=True)
                self.coverage_log.append(dict(period=t, territory=terr, motion="SMB",
                                              candidates=len(cands), capacity=cap))
                self._work(cands[:cap], t, season, quarter_end)

            # --- Named motion: controlled-entity opps, global capacity ---
            named_cap = len(self.named_reps) * cfg.rep_cap
            named_cands = []
            for terr in p.territories:
                named_cands += [o for o in self._opps_by_terr_motion.get((terr, "Named"), [])
                                if (not o["_closed"]) and o["_created_idx"] <= t]
            named_cands.sort(key=lambda o: self.assumed.score(self.acc_by_id[o["AccountId"]]), reverse=True)
            self.coverage_log.append(dict(period=t, territory="GLOBAL", motion="Named",
                                          candidates=len(named_cands), capacity=named_cap))
            self._work(named_cands[:named_cap], t, season, quarter_end)

            # --- PDCA: nudge assumed weights toward the realized signal ---
            self.assumed.pdca_update(self.opps, self.acc_by_id, t)

        self._build_activities()
        self._build_usage()
        return self

    def _auto_close_stale(self, t: int, cap_months: int) -> None:
        """Bound days-open: any opp open past the cap is auto-closed as lost (capped, not 1,200 days)."""
        for o in self.opps:
            if (not o["_closed"]) and o["_created_idx"] <= t and (t - o["_created_idx"]) >= cap_months:
                acc = self.acc_by_id[o["AccountId"]]
                self._close(o, acc, t, won=False)

    def _work(self, worked: list[dict], t: int, season: float, quarter_end: bool) -> None:
        for o in worked:
            acc = self.acc_by_id[o["AccountId"]]
            p_win = self.true.win_prob(acc, season, o["_src_true"])
            if not o["OwnerId"]:
                o["OwnerId"] = self._assign_owner(acc)
            if o["_true_stage_idx"] == 0:
                o["_true_stage_idx"] = 1                       # moved out of Prospecting

            if self.rng.random() < 0.40:                       # resolves this period
                won = self.rng.random() < p_win
                self._close(o, acc, t, won=won, quarter_end=quarter_end)
            else:                                              # advance stage, stay open
                if o["_true_stage_idx"] < 4:
                    o["_true_stage_idx"] += 1

    def _close(self, o: dict, acc: dict, t: int, won: bool, quarter_end: bool = False) -> None:
        cfg = self.cfg
        o["_closed"], o["_won"], o["_true_close_idx"] = True, won, t
        o["_true_stage_idx"] = STAGES.index(WON_STAGE if won else LOST_STAGE)
        o["Amount"] = round(self.true.account_value(acc), -2)
        if not won:
            o["LossReason"] = self.rng.choices(
                self.p.loss_reasons,
                weights=[self.p.loss_profile[acc["Segment"]][r] for r in self.p.loss_reasons])[0]
        o["_rec_close_idx"] = self.reps.recorded_close_idx(
            t, won, quarter_end, self.rng, cfg.t_periods - 1)
        o["Source"] = self.reps.observed_source(o["_src_true"], won, self.rng)

    def _assign_owner(self, acc: dict) -> str:
        if acc["_true_ce"]:
            return self.rng.choice(self.named_reps)["OwnerId"]
        reps = self.smb_reps_by_terr[acc["Territory"]]
        return self.rng.choice(reps)["OwnerId"] if reps else self.named_reps[0]["OwnerId"]

    def _build_activities(self) -> None:
        acts = []
        aid = 0
        for o in self.opps:
            n = self.rng.randint(2, 9)
            for _ in range(n):
                aid += 1
                acts.append(dict(ActivityId=f"AC{aid:07d}", OppId=o["OppId"],
                                 ActivityType=self.rng.choice(["Call", "Email", "Meeting", "Demo"]),
                                 ActivityDate=o["CreatedDate"], OwnerId=o["OwnerId"] or "U001",
                                 DurationMin=self.rng.choice([15, 30, 45, 60])))
        self.activities = acts

    def _build_usage(self) -> None:
        cfg, p = self.cfg, self.p
        won_accs = {}
        for o in self.opps:
            if o["_won"]:
                won_accs[o["AccountId"]] = o
        usage_rows, health_rows = [], []
        uid = 0
        for acc_id, o in won_accs.items():
            acc = self.acc_by_id[acc_id]
            profile = self.rng.choices(p.usage_profiles, weights=p.usage_profile_w)[0]
            base = 0.30 + 0.5 * acc["_engagement"]              # tied to the true value driver
            seats = self.rng.choice([5, 10, 20, 50, 100])
            traj = []
            for m in range(6):
                if profile == "growing":
                    r = base + m * 0.03
                elif profile == "declining":
                    r = base - m * 0.04
                elif profile == "spiky":
                    r = base + self.rng.uniform(-0.15, 0.15)
                else:
                    r = base + self.rng.uniform(-0.04, 0.04)
                r = min(max(r, 0.05), 0.98)
                traj.append(r)
                uid += 1
                usage_rows.append(dict(UsageId=f"U{uid:07d}", AccountId=acc_id,
                                       Month=month_index_to_date(cfg.start_year, cfg.start_month, 12 + m),
                                       Seats=seats, MAU=int(seats * r), MAURatio=round(r, 3)))
            mean_r = sum(traj) / len(traj)
            slope = traj[-1] - traj[0]
            score = int(min(95, max(15, 55 + 60 * (mean_r - 0.5) + 80 * slope)))
            band = "Green" if score >= 75 else ("Yellow" if score >= 50 else "Red")
            nps = int(min(80, max(-40, (score - 55) * 1.3 + self.rng.uniform(-10, 10))))
            health_rows.append(dict(AccountId=acc_id, HealthScore=score, HealthBand=band,
                                    NPS=nps, _usage_mean=round(mean_r, 3)))
        self.usage = usage_rows
        self.health = health_rows

    # ----- emit (delegated) ----------------------------------------------- #
    def emit(self, out_dir):
        from .emit import emit as _emit
        return _emit(self, out_dir)
