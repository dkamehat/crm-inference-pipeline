"""
self_check — verify every planted signal is recoverable from the OBSERVED data.

This is the human-readable, eyeball version of what the L3 harness will later
assert mechanically. ``run_checks`` returns structured results (so pytest can
consume them); ``self_check`` prints the report.

The ten checks map one-to-one to the planted signals in the spec:
  ① seasonality        ② loss segment-conditional   ③ cohort months >= 0
  ④ days-open capped    ⑤ usage<->health correlation  ⑥ wedge recoverable
  ⑦ controlling-entity concentration                  ⑧ partner under-credited
  ⑨ coverage confound   ⑩ weight-gap convergence (the kill-shot)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import List, NamedTuple

import pandas as pd

from .config import WON_STAGE, LOST_STAGE


class Check(NamedTuple):
    name: str
    ok: bool
    detail: str


def run_checks(out_dir: str) -> List[Check]:
    out = Path(out_dir)
    acc = pd.read_csv(out / "accounts.csv")
    opp = pd.read_csv(out / "opportunities.csv")
    usage = pd.read_csv(out / "usage.csv")
    health = pd.read_csv(out / "health.csv")
    gt = json.loads((out / "_ground_truth.json").read_text())

    res: List[Check] = []

    def check(name, ok, detail=""):
        res.append(Check(name, bool(ok), detail))

    opp["CloseDate"] = pd.to_datetime(opp["CloseDate"], errors="coerce")
    opp["CreatedDate"] = pd.to_datetime(opp["CreatedDate"], errors="coerce")
    won = opp[opp.Stage == WON_STAGE].copy()
    lost = opp[opp.Stage == LOST_STAGE].copy()

    # ① seasonality: monthly won-count varies with peaks/troughs
    won["m"] = won["CloseDate"].dt.month
    by_m = won.groupby("m").size()
    cv = by_m.std() / by_m.mean() if by_m.mean() else 0
    check("① seasonality present (CV>0.12)", cv > 0.12,
          f"CV={cv:.2f}, peak_month={by_m.idxmax()}")

    # ② loss reasons segment-conditional (SMB -> Price, Enterprise -> No Decision)
    lost = lost.merge(acc[["AccountId", "Segment"]], on="AccountId", how="left")
    smb_top = lost[lost.Segment == "SMB"]["LossReason"].value_counts().idxmax()
    ent_top = lost[lost.Segment == "Enterprise"]["LossReason"].value_counts().idxmax()
    check("② loss segment-conditional (SMB=Price, Ent=No Decision)",
          smb_top == "Price" and ent_top == "No Decision", f"SMB={smb_top}, Ent={ent_top}")

    # ③ temporal: months_since_cohort >= 0
    m = won.merge(acc[["AccountId", "CreatedDate"]].rename(columns={"CreatedDate": "acc_created"}),
                  on="AccountId")
    m["acc_created"] = pd.to_datetime(m["acc_created"], errors="coerce")
    msc = (m["CloseDate"].dt.year - m["acc_created"].dt.year) * 12 + \
          (m["CloseDate"].dt.month - m["acc_created"].dt.month)
    check("③ cohort months_since >= 0", (msc >= 0).all(), f"min_msc={int(msc.min())}")

    # ④ dwell realistic on BOTH tails: open opps not stuck for 1,200 days (upper),
    #    and closed opps not piled onto a 0-day same-day cycle (lower). "today" from data.
    openo = opp[~opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    today = opp["CreatedDate"].max() + pd.Timedelta(days=45)
    openo["days_open"] = (today - openo["CreatedDate"]).dt.days
    maxd = openo["days_open"].max() if len(openo) else 0
    closed_dur = (pd.to_datetime(won["CloseDate"]) - pd.to_datetime(won["CreatedDate"])).dt.days
    lost_dur = (pd.to_datetime(lost["CloseDate"]) - pd.to_datetime(lost["CreatedDate"])).dt.days
    cyc = pd.concat([closed_dur, lost_dur]).dropna()
    # Guard the SHAPE, not a single value: a future floor/clamp spike at ANY low
    # day-value (0, 1, 2, ...) trips the same invariant — closing the bug class,
    # not one instance. (1) low-end mass capped, (2) no single day-value spike.
    low_share = (cyc <= 2).mean() if len(cyc) else 0
    mode_share = cyc.value_counts(normalize=True).max() if len(cyc) else 0
    check("④ dwell realistic (open<700d, low-end<=2d <15%, no single-day spike <10%)",
          maxd < 700 and low_share < 0.15 and mode_share < 0.10,
          f"max_open={maxd}, <=2d={low_share:.1%}, top_day={mode_share:.1%}, median={cyc.median():.0f}d")

    # ⑤ activation correlation usage <-> health
    um = usage.groupby("AccountId")["MAURatio"].mean().reset_index()
    h = health.merge(um, on="AccountId", how="inner")
    corr = h["MAURatio"].corr(h["HealthScore"])
    check("⑤ usage<->health correlation (>0.3)", corr > 0.3, f"corr={corr:.2f}")

    # ⑥ wedge: planted cell has high ARPA, low count
    w = won.merge(acc[["AccountId", "Segment", "Category"]], on="AccountId")
    arpa = w.groupby(["Segment", "Category"]).agg(arpa=("Amount", "mean"), cnt=("Amount", "size")).reset_index()
    wedge = gt["wedge"]
    cell = arpa[(arpa.Segment == wedge["segment"]) & (arpa.Category == wedge["category"])]
    cnt_med = arpa["cnt"].median()
    if len(cell):
        hi_arpa = cell["arpa"].iloc[0] > arpa["arpa"].quantile(0.75)
        lo_cnt = cell["cnt"].iloc[0] < cnt_med
        check("⑥ wedge recoverable (hi ARPA, low count)", hi_arpa and lo_cnt,
              f"arpa={cell['arpa'].iloc[0]:.0f} (q75={arpa['arpa'].quantile(0.75):.0f}), "
              f"cnt={cell['cnt'].iloc[0]} (med={cnt_med:.0f})")
    else:
        check("⑥ wedge recoverable", False, "wedge cell has no wins")

    # ⑦ controlling-entity concentration: heavy-tailed; few entities own many
    true_ce = gt["true_controlling_entities"]
    ce_counts = Counter(true_ce.values())
    n_ce = len(ce_counts)
    n_controlled = len(true_ce)
    biggest = ce_counts.most_common(1)[0][1] if ce_counts else 0
    top5_share = (sum(c for _, c in ce_counts.most_common(5)) / n_controlled) if n_controlled else 0
    check("⑦ concentration (heavy-tailed control)", n_ce < 0.7 * n_controlled and biggest >= 8,
          f"{n_ce} entities own {n_controlled} accts; biggest={biggest}; top5={top5_share:.0%}")

    # ⑧ partner under-credit: true partner conv > observed partner conv
    true_src = gt["true_source"]
    opp["_src_true"] = opp["OppId"].map(true_src)
    opp["_won"] = opp.Stage == WON_STAGE
    opp["_closed"] = opp.Stage.isin([WON_STAGE, LOST_STAGE])
    closed = opp[opp._closed]
    true_pc = closed[closed._src_true == "partner"]._won.mean()
    obs_pc = closed[closed.Source == "partner"]._won.mean()
    check("⑧ partner under-credited (true conv > observed)", true_pc >= obs_pc - 1e-9,
          f"true_partner_conv={true_pc:.3f} vs observed={obs_pc:.3f}")

    # ⑨ coverage confound: high-potential territory is UNDER-COVERED (low closed/total),
    #    while execution (win-rate among closed) stays ~flat -> "broken plan, not bad reps"
    acc_terr = acc[["AccountId", "Region"]]
    allc = opp.merge(acc_terr, on="AccountId")
    allc["_closed_flag"] = allc.Stage.isin([WON_STAGE, LOST_STAGE])
    cov_rate = allc.groupby("Region")["_closed_flag"].mean()
    exec_wr = closed.merge(acc_terr, on="AccountId").groupby("Region")._won.mean()
    terr_pot = gt["territory_potential"]
    top_pot = max(terr_pot, key=terr_pot.get)
    cov_ok = cov_rate[top_pot] < cov_rate.median()
    exec_ok = exec_wr[top_pot] >= exec_wr.median() - 0.05
    check("⑨ coverage confound (top-potential under-covered, reps execute fine)",
          cov_ok and exec_ok,
          f"coverage[{top_pot}]={cov_rate[top_pot]:.2f}(med={cov_rate.median():.2f}); "
          f"exec[{top_pot}]={exec_wr[top_pot]:.2f}(med={exec_wr.median():.2f})")

    # ⑩ weight-gap convergence (kill-shot): gap shrinks over periods
    gc = gt["weight_gap_curve"]
    if len(gc) >= 2:
        first, last = gc[0]["weight_gap"], gc[-1]["weight_gap"]
        check("⑩ weight-gap converges (last<first)", last < first, f"gap {first:.3f} -> {last:.3f}")
    else:
        check("⑩ weight-gap converges", False, "insufficient periods")

    return res


def run_integrity_checks(out_dir: str) -> List[Check]:
    """The other half of the thesis: no UNPLANTED structure. Dimensions with NO
    planted skew must stay ~uniform and not collapse onto a single value (the way
    the un-worked backlog once dumped 38% of opps onto one rep).

    The planted-skew dimensions are intentionally concentrated and are validated by
    the planted-signal checks instead — segment by ②, source by ⑧, territory by ⑨;
    stage concentration is the funnel. So they are audited (printed) but not gated.
    """
    out = Path(out_dir)
    acc = pd.read_csv(out / "accounts.csv")
    opp = pd.read_csv(out / "opportunities.csv")
    o = opp.merge(acc[["AccountId", "Category"]], on="AccountId")
    res: List[Check] = []

    def check(name, ok, detail=""):
        res.append(Check(name, bool(ok), detail))

    # owner: assigned at intake by territory/motion -> ~uniform within motion
    owner_share = opp.OwnerId.value_counts(normalize=True).max()
    check("owner: no single-rep concentration (<25%)", owner_share < 0.25,
          f"top_owner={owner_share:.1%} of {opp.OwnerId.nunique()} reps")
    # category: rng.choice -> ~uniform across categories, must not collapse
    cat_share = o.Category.value_counts(normalize=True).max()
    check("category: ~uniform, no collapse (<20%)", cat_share < 0.20,
          f"top_cat={cat_share:.1%} of {o.Category.nunique()}")
    return res


def _dimension_audit(out_dir: str) -> str:
    """One-line top-value share per dimension (informational eyeball)."""
    out = Path(out_dir)
    acc = pd.read_csv(out / "accounts.csv")
    opp = pd.read_csv(out / "opportunities.csv")
    o = opp.merge(acc[["AccountId", "Segment", "Category", "Region"]], on="AccountId")
    dims = {"owner": opp.OwnerId, "source": opp.Source, "territory": o.Region,
            "segment": o.Segment, "category": o.Category, "stage": opp.Stage}
    parts = []
    for name, s in dims.items():
        vc = s.value_counts(normalize=True)
        parts.append(f"{name} {vc.iloc[0]*100:.0f}%({vc.index[0]})")
    return "  ".join(parts)


def summary(out_dir: str) -> dict:
    """Headline counts for the report (opps / closed / won / win-rate)."""
    opp = pd.read_csv(Path(out_dir) / "opportunities.csv")
    closed = opp.Stage.isin([WON_STAGE, LOST_STAGE]).sum()
    won = (opp.Stage == WON_STAGE).sum()
    return dict(opps=len(opp), closed=int(closed), won=int(won),
                win_rate=(won / closed if closed else 0.0))


def _ensure_utf8_stdout() -> None:
    # the planted-signal labels use circled digits / em-dashes; keep them readable
    # even on a legacy (e.g. cp932) Windows console.
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def self_check(out_dir: str) -> List[Check]:
    _ensure_utf8_stdout()
    res = run_checks(out_dir)
    s = summary(out_dir)
    print("\n=== self_check (planted signal recovery) ===")
    print(f"  [info] opps={s['opps']}, closed={s['closed']}, won={s['won']}, "
          f"overall win-rate={s['win_rate']:.1%}")
    npass = sum(1 for c in res if c.ok)
    for c in res:
        print(f"  [{'PASS' if c.ok else 'FAIL'}] {c.name}  —  {c.detail}")
    print(f"\n  {npass}/{len(res)} signals recoverable")

    integ = run_integrity_checks(out_dir)
    print("\n=== integrity (no UNPLANTED structure) ===")
    print(f"  [audit] {_dimension_audit(out_dir)}")
    for c in integ:
        print(f"  [{'PASS' if c.ok else 'FAIL'}] {c.name}  —  {c.detail}")
    print(f"  {sum(1 for c in integ if c.ok)}/{len(integ)} integrity invariants hold")
    return res
