"""
Pytest suite for the L0 WorldModel.

Two groups:
  - the ten planted-signal recovery checks (the eyeball self_check, asserted)
  - DoD structural invariants: opp.created >= account.created, days-open capped,
    manifest schema, and seed reproducibility.

A module-scoped fixture generates one dataset; the signal checks run against it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# make the package importable whether or not it's installed
PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

import random

from world_model.config import Config, V1_PROFILE, WON_STAGE, LOST_STAGE, MAX_OPEN_STAGE_IDX, STAGES
from world_model.reps import RepBehaviorModel
from world_model.simulate import WorldModel
from world_model.self_check import run_checks


def _generate(out_dir: Path, seed: int = 42, periods: int = 18) -> Path:
    cfg = Config(seed=seed, t_periods=periods)
    WorldModel(cfg, V1_PROFILE).simulate().emit(out_dir)
    return out_dir


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("v1_out")
    return _generate(out)


# --- planted-signal recovery (the ten self_check assertions) ---------------- #

def test_all_planted_signals_recoverable(dataset):
    results = run_checks(str(dataset))
    assert len(results) == 10, "expected ten planted-signal checks"
    failed = [f"{c.name} — {c.detail}" for c in results if not c.ok]
    assert not failed, "planted signals not recovered:\n  " + "\n  ".join(failed)


def test_each_signal_individually(dataset):
    # surfaces exactly which signal regressed if one breaks
    for c in run_checks(str(dataset)):
        assert c.ok, f"{c.name} failed: {c.detail}"


# --- DoD structural invariants ---------------------------------------------- #

def test_opp_created_not_before_account_created(dataset):
    acc = pd.read_csv(dataset / "accounts.csv")[["AccountId", "CreatedDate"]]
    opp = pd.read_csv(dataset / "opportunities.csv")[["AccountId", "CreatedDate"]]
    merged = opp.merge(acc, on="AccountId", suffixes=("_opp", "_acc"))
    opp_created = pd.to_datetime(merged["CreatedDate_opp"])
    acc_created = pd.to_datetime(merged["CreatedDate_acc"])
    assert (opp_created >= acc_created).all(), "found opp.created < account.created"


def test_close_date_not_before_opp_created(dataset):
    """opp <= close. close-optimism may pull the recorded close earlier within the
    deal's life, but never before the opp was created (no negative duration / defect #3)."""
    opp = pd.read_csv(dataset / "opportunities.csv")
    closed = opp[opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    closed = closed[closed.CloseDate.astype(str).str.len() > 0]
    created = pd.to_datetime(closed["CreatedDate"])
    close = pd.to_datetime(closed["CloseDate"])
    bad = int((close < created).sum())
    assert bad == 0, f"{bad} closed opps have CloseDate before CreatedDate"


def test_temporal_integrity_triangle(dataset):
    """The full triangle closes: account.created <= opp.created <= close.
    This is the invariant whose absence let two distortion-direction bugs through."""
    acc = pd.read_csv(dataset / "accounts.csv")[["AccountId", "CreatedDate"]]
    opp = pd.read_csv(dataset / "opportunities.csv")
    closed = opp[opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    closed = closed[closed.CloseDate.astype(str).str.len() > 0]
    m = closed.merge(acc.rename(columns={"CreatedDate": "acc_created"}), on="AccountId")
    acc_c = pd.to_datetime(m["acc_created"])
    opp_c = pd.to_datetime(m["CreatedDate"])
    close_c = pd.to_datetime(m["CloseDate"])
    assert (acc_c <= opp_c).all(), "account.created > opp.created"
    assert (opp_c <= close_c).all(), "opp.created > close"


def test_autoclose_side_effects_consistent(dataset):
    """auto-close (and every close) must leave consistent records: a closed opp has
    a positive Amount; Closed Lost carries a valid LossReason; Closed Won carries none."""
    opp = pd.read_csv(dataset / "opportunities.csv")
    won = opp[opp.Stage == WON_STAGE]
    lost = opp[opp.Stage == LOST_STAGE]
    valid_reasons = set(V1_PROFILE.loss_reasons)
    # every closed opp has a real (rounded, positive) amount
    assert (won["Amount"] > 0).all(), "Closed Won opp with non-positive Amount"
    assert (lost["Amount"] > 0).all(), "Closed Lost opp with non-positive Amount"
    # loss reasons: present and valid for lost, absent for won
    assert lost["LossReason"].notna().all(), "Closed Lost opp missing LossReason"
    assert set(lost["LossReason"].unique()).issubset(valid_reasons), "unknown LossReason value"
    assert won["LossReason"].isna().all() or (won["LossReason"].astype(str) == "").all(), \
        "Closed Won opp carries a LossReason"


def test_close_cycle_lower_tail(dataset):
    """Dwell realism on the LOWER tail: closes must not pile onto a 0-day same-day
    cycle (the clamp-induced artifact). Guards defect #4 from the fast end."""
    opp = pd.read_csv(dataset / "opportunities.csv")
    closed = opp[opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    closed = closed[closed.CloseDate.astype(str).str.len() > 0]
    cyc = (pd.to_datetime(closed["CloseDate"]) - pd.to_datetime(closed["CreatedDate"])).dt.days
    zero_ratio = (cyc <= 0).mean()
    assert zero_ratio < 0.15, f"too many 0-day closes: {zero_ratio:.1%} (cycle median {cyc.median():.0f}d)"


@pytest.mark.parametrize("seed", [42, 7, 123])
def test_temporal_invariants_multi_seed(tmp_path, seed):
    """Harden the temporal triangle across seeds (the prior bugs were ~40% prevalence,
    but cheap multi-seed coverage guards against seed-specific regressions)."""
    out = _generate(tmp_path / f"s{seed}", seed=seed)
    acc = pd.read_csv(out / "accounts.csv")[["AccountId", "CreatedDate"]]
    opp = pd.read_csv(out / "opportunities.csv")
    closed = opp[opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    closed = closed[closed.CloseDate.astype(str).str.len() > 0]
    m = closed.merge(acc.rename(columns={"CreatedDate": "acc_created"}), on="AccountId")
    acc_c = pd.to_datetime(m["acc_created"])
    opp_c = pd.to_datetime(m["CreatedDate"])
    close_c = pd.to_datetime(m["CloseDate"])
    assert (acc_c <= opp_c).all(), f"[seed {seed}] account.created > opp.created"
    assert (opp_c <= close_c).all(), f"[seed {seed}] opp.created > close"
    cyc = (close_c - opp_c).dt.days
    assert (cyc <= 0).mean() < 0.15, f"[seed {seed}] too many 0-day closes"


def test_days_open_capped(dataset):
    opp = pd.read_csv(dataset / "opportunities.csv")
    opp["CreatedDate"] = pd.to_datetime(opp["CreatedDate"])
    openo = opp[~opp.Stage.isin([WON_STAGE, LOST_STAGE])].copy()
    today = opp["CreatedDate"].max() + pd.Timedelta(days=45)
    days_open = (today - openo["CreatedDate"]).dt.days
    assert days_open.max() < 700, f"impossible stuck opp: max days_open={days_open.max()}"


def test_manifest_schema(dataset):
    gt = json.loads((dataset / "_ground_truth.json").read_text())
    required = {
        "profile", "seed", "config", "true_cat_w", "cat_value_mult",
        "assumed_cat_w_final", "wedge", "source_logit", "attrib_leak",
        "true_controlling_entities", "true_source", "weight_gap_curve",
        "territory_potential",
    }
    assert required.issubset(gt), f"manifest missing keys: {required - set(gt)}"
    assert set(gt["wedge"]) == {"segment", "category"}
    assert "out_dir" not in gt["config"], "manifest must not leak a volatile output path"
    assert len(gt["weight_gap_curve"]) >= 2


def test_seed_reproducible(tmp_path):
    a = _generate(tmp_path / "a")
    b = _generate(tmp_path / "b")
    for name in ["accounts.csv", "opportunities.csv", "users.csv",
                 "activities.csv", "usage.csv", "health.csv", "assumed_scores.csv"]:
        assert (a / name).read_bytes() == (b / name).read_bytes(), f"{name} not reproducible"
    assert (a / "_ground_truth.json").read_text() == (b / "_ground_truth.json").read_text()


def test_stage_lag_never_inflates_recorded_stage():
    """Stage-lag means 'the rep didn't update it' — the recorded stage must fall
    BEHIND true progress, never ahead. This guards the direction of the distortion
    (the bug that slipped through was `max(1, idx-1)` inflating un-worked opps).
    """
    # force the stage-lag branch (no happy-ears) and sweep every true stage
    reps = RepBehaviorModel(Config(stage_lag_p=1.0, happy_p=0.0), V1_PROFILE)
    rng = random.Random(0)
    for true_idx in range(len(STAGES)):
        for _ in range(200):
            rec = reps.recorded_open_stage_idx(true_idx, rng)
            assert rec <= true_idx, f"stage-lag inflated: true={true_idx} -> recorded={rec}"
            assert rec >= 0, f"recorded stage below 0: {rec}"


def test_happy_ears_capped_at_open_ceiling():
    """Happy-ears may record AHEAD, but never past the last open stage (cannot
    fabricate a closed/won record from an open opp)."""
    reps = RepBehaviorModel(Config(stage_lag_p=0.0, happy_p=1.0), V1_PROFILE)
    rng = random.Random(0)
    for true_idx in range(MAX_OPEN_STAGE_IDX + 1):
        for _ in range(200):
            rec = reps.recorded_open_stage_idx(true_idx, rng)
            assert rec <= MAX_OPEN_STAGE_IDX, f"happy-ears past open ceiling: {rec}"
            assert rec <= true_idx + 1, f"happy-ears jumped >1 stage: {true_idx}->{rec}"


def test_different_seed_differs(tmp_path):
    a = _generate(tmp_path / "s42", seed=42)
    b = _generate(tmp_path / "s7", seed=7)
    assert (a / "opportunities.csv").read_bytes() != (b / "opportunities.csv").read_bytes()


def test_wedge_is_structural_blind_spot_not_transient_prior(dataset):
    """spec §8 #1: the wedge survives PDCA — it stays under-worked *after* the weight
    gap has converged, because the score optimizes conversion and never sees value.

    Two assertions together make it a structural blind spot rather than a stale prior:
      (a) the org HAS learned: the wedge category's assumed weight converged to the true
          weight (the initial miscalibration is substantially corrected); yet
      (b) the wedge cell is STILL under-worked late: among late-created opps, the wedge
          cell's closed-rate (a proxy for being worked) is below the global closed-rate.
    """
    acc = pd.read_csv(dataset / "accounts.csv")
    opp = pd.read_csv(dataset / "opportunities.csv")
    gt = json.loads((dataset / "_ground_truth.json").read_text())
    wseg, wcat = gt["wedge"]["segment"], gt["wedge"]["category"]

    # (a) learning happened: assumed weight for the wedge category converged toward true
    tw = gt["true_cat_w"][wcat]
    aw = gt["assumed_cat_w_final"][wcat]
    prior_bias = gt["config"]["prior_bias"]
    assert abs(aw - tw) < prior_bias, (
        f"wedge weight did not converge (no learning): assumed={aw:.3f} true={tw:.3f}")

    # (b) still under-worked in the LATE half of the horizon
    o = opp.merge(acc[["AccountId", "Segment", "Category"]], on="AccountId")
    o["created_m"] = pd.to_datetime(o["CreatedDate"]).dt.to_period("M")
    months = sorted(o["created_m"].unique())
    late = set(months[len(months) // 2:])
    o_late = o[o["created_m"].isin(late)].copy()
    o_late["closed"] = o_late.Stage.isin([WON_STAGE, LOST_STAGE])
    wedge_rate = o_late[(o_late.Segment == wseg) & (o_late.Category == wcat)]["closed"].mean()
    global_rate = o_late["closed"].mean()
    assert wedge_rate < global_rate, (
        f"wedge not under-worked late: wedge closed-rate={wedge_rate:.2f} "
        f">= global={global_rate:.2f} (would mean PDCA corrected it)")
