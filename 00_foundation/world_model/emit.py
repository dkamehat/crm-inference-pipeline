"""
Emit the OBSERVED tables (the lossy projection analysis sees) and the
ground-truth manifest (the answer key only the harness sees).

Observed CSVs (Salesforce-shaped, aligned with the existing Phase-1 schema):
  accounts, opportunities, assumed_scores, users, activities, usage, health

The manifest records the hidden truth — true weights, the true ownership graph,
true source conversion, the planted wedge, the weight-gap curve, territory
potential — and deliberately contains NO volatile paths.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .config import STAGES, TERMINAL_STAGES
from .timeutil import add_days


def emit(wm, out_dir) -> Path:
    cfg, p = wm.cfg, wm.p
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- accounts: controlling entity hidden / mis-parented in the observed CRM ---
    acc_rows = []
    for a in wm.accounts:
        ce_obs = wm.graph.observed_ce(a["_true_ce"], wm.rng)
        acc_rows.append(dict(
            AccountId=a["AccountId"], AccountName=a["AccountName"],
            Segment=a["Segment"], Category=a["Category"], Region=a["Territory"],
            ControllingEntityId=ce_obs, CreatedDate=a["CreatedDate"],
        ))
    pd.DataFrame(acc_rows).to_csv(out / "accounts.csv", index=False)

    # --- opportunities + assumed scores ---
    opp_rows, assumed_rows = [], []
    for o in wm.opps:
        acc = wm.acc_by_id[o["AccountId"]]
        if o["_closed"]:
            rec_stage = STAGES[o["_true_stage_idx"]]                    # terminal stage as recorded
            # Day-level recorded close: a whole-month gap to the recorded close period
            # plus a positive within-month offset = the base cycle. Close-optimism pulls
            # the record earlier but is BOUNDED by the cycle (you cannot record a deal as
            # closing earlier than it could physically have progressed), so it never
            # collapses short same-period cycles onto a floor. cycle >= ceil(base/2) >= 2.
            months_gap = max(0, o["_rec_close_idx"] - o["_created_idx"])
            within = wm.rng.randint(3, 25)                              # within-month day offset
            base_cycle = months_gap * 30 + within
            optimism = min(wm.reps.close_optimism_offset(wm.rng), base_cycle // 2)
            cycle_days = base_cycle - optimism
            close_date = add_days(o["CreatedDate"], cycle_days)
        else:
            rec_idx = wm.reps.recorded_open_stage_idx(o["_true_stage_idx"], wm.rng)  # happy-ears
            rec_stage = STAGES[rec_idx]
            close_date = ""
        opp_rows.append(dict(
            OppId=o["OppId"], AccountId=o["AccountId"], Stage=rec_stage,
            Amount=o["Amount"], Source=o["Source"], OwnerId=o["OwnerId"] or "U001",
            CreatedDate=o["CreatedDate"], CloseDate=close_date, LossReason=o["LossReason"],
        ))
        assumed_rows.append(dict(OppId=o["OppId"], AccountId=o["AccountId"],
                                 AssumedScore=round(wm.assumed.score(acc), 4)))
    pd.DataFrame(opp_rows).to_csv(out / "opportunities.csv", index=False)
    pd.DataFrame(assumed_rows).to_csv(out / "assumed_scores.csv", index=False)

    pd.DataFrame(wm.users)[["OwnerId", "OwnerName", "Motion", "Region"]].to_csv(out / "users.csv", index=False)
    pd.DataFrame(wm.activities).to_csv(out / "activities.csv", index=False)
    pd.DataFrame(wm.usage).to_csv(out / "usage.csv", index=False)
    pd.DataFrame(wm.health)[["AccountId", "HealthScore", "HealthBand", "NPS"]].to_csv(out / "health.csv", index=False)

    # --- GROUND-TRUTH MANIFEST (the answer key; no volatile paths) ---
    manifest = dict(
        profile=p.name,
        seed=cfg.seed,
        config=asdict(cfg),
        true_cat_w=wm.true.true_cat_w,
        cat_value_mult=wm.true.cat_value_mult,
        assumed_cat_w_final=wm.assumed.assumed_cat_w,
        wedge=dict(segment=p.wedge_segment, category=p.wedge_category),
        source_logit=p.source_logit,
        true_source_lift=p.source_true_lift,
        attrib_leak=p.attrib_leak,
        true_controlling_entities={a["AccountId"]: a["_true_ce"] for a in wm.accounts if a["_true_ce"]},
        true_source={o["OppId"]: o["_src_true"] for o in wm.opps},
        weight_gap_curve=wm.assumed.gap_curve,
        territory_potential=p.terr_potential,
    )
    (out / "_ground_truth.json").write_text(json.dumps(manifest, indent=2))
    return out
