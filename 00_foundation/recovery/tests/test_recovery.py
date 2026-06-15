"""
Pytest suite for the L1 recovery layer (spec §10).

Groups mirror L0's discipline: contract / firewall / invariant / guard(form) /
absence / quirk(reference-habit audit) / output. Probabilistic tests run over
seed [42, 7, 123]. Naming: test_<subject>_<property>; docstrings state the
invariant. L1 never self-grades recovery on the real observation — synthetic,
test-controlled data is used to validate the *method* (that is not the manifest).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from recovery import io, baseline as bl, card as cardmod
from recovery.card import build_card, CARD_SCHEMA
from recovery.wedge import (recover, _category_effects, _segment_adjusted,
                            _count_percentile)
from recovery import guards

SEEDS = [42, 7, 123]
WON = "06 - Closed Won"


# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #
def synth_won(seed: int, n: int = 900, wedge="C3", wedge_mult=3.2,
              wedge_seg_bias=None) -> pd.DataFrame:
    """Synthetic won frame matching the multiplicative generative form
    (Amount = base·seg_mult·cat_mult·(0.5+eng)), with one rare high-value category.
    Fully synthetic — no real domain, safe to commit as a fixture (spec §11)."""
    r = np.random.default_rng(seed)
    segs = ["S1", "S2", "S3"]
    seg_mult = {"S1": 0.4, "S2": 1.0, "S3": 2.6}
    cats = [f"C{i}" for i in range(8)]
    cat_mult = {c: float(r.uniform(0.7, 1.3)) for c in cats}
    cat_mult[wedge] = wedge_mult
    p = np.ones(8)
    p[cats.index(wedge)] = 0.12          # rare
    p = p / p.sum()
    seg = r.choice(segs, n, p=[0.62, 0.30, 0.08])
    cat = r.choice(cats, n, p=p)
    if wedge_seg_bias is not None:        # concentrate wedge in a given segment
        mask = cat == wedge
        seg[mask] = wedge_seg_bias
    eng = r.random(n)
    amt = 8000 * np.array([seg_mult[s] for s in seg]) * \
        np.array([cat_mult[c] for c in cat]) * (0.5 + eng)
    amt = np.round(amt, -2)
    return pd.DataFrame({"OppId": [f"O{i}" for i in range(n)],
                         "AccountId": [f"A{i % (n // 2)}" for i in range(n)],
                         "Stage": WON, "Amount": amt, "Segment": seg, "Category": cat})


def null_won(seed: int) -> pd.DataFrame:
    """Synth then break Amount⊥category by permuting the Category column."""
    w = synth_won(seed)
    r = np.random.default_rng(seed + 1)
    w["Category"] = r.permutation(w["Category"].to_numpy())
    return w


@pytest.fixture(scope="module")
def real_obs(tmp_path_factory):
    """Generate the real V1 observation via the L0 generator into a temp dir.
    (Tests may import world_model; the recovery PACKAGE may not — firewall.)"""
    import world_model.config as wmc
    from world_model.simulate import WorldModel
    out = tmp_path_factory.mktemp("obs_v1")
    WorldModel(wmc.Config(seed=42), wmc.V1_PROFILE).simulate().emit(out)
    acc, opp = out / "accounts.csv", out / "opportunities.csv"
    return {"dir": out, "acc": acc, "opp": opp, "won": io.load_won(acc, opp)}


@pytest.fixture(scope="module")
def real_result(real_obs):
    return recover(real_obs["won"], n_perm=400, n_bootstrap=80, seed=42)


def _build(real_obs, result):
    leak, _ = io.audit_columns(real_obs["acc"], real_obs["opp"])
    return build_card(result, observation_hash=io.observation_hash(real_obs["acc"], real_obs["opp"]),
                      won_filter=WON, baseline=bl.baseline_flags(real_obs["won"]),
                      no_truth_leak=leak, no_false_wedge_owner_region=True)


def _assert_schema(node, schema, path=""):
    assert isinstance(node, dict), f"{path}: expected dict"
    assert set(node) == set(schema), f"{path}: keys {set(node)} != {set(schema)}"
    for k, exp in schema.items():
        v = node[k]
        if isinstance(exp, dict):
            _assert_schema(v, exp, f"{path}.{k}")
        else:
            assert isinstance(v, exp), f"{path}.{k}: {type(v).__name__} != {exp.__name__}"


# --------------------------------------------------------------------------- #
# contract
# --------------------------------------------------------------------------- #
def test_card_schema_is_complete_and_typed(real_obs, real_result):
    """The card matches the §12 schema exactly (keys and types)."""
    _assert_schema(_build(real_obs, real_result), CARD_SCHEMA)


def test_card_is_seed_reproducible(real_obs):
    """Same observation + seed => byte-identical card."""
    a = json.dumps(_build(real_obs, recover(real_obs["won"], n_perm=300, n_bootstrap=40, seed=5)))
    b = json.dumps(_build(real_obs, recover(real_obs["won"], n_perm=300, n_bootstrap=40, seed=5)))
    assert a == b


def test_observation_contract_is_minimal(real_obs):
    """load_won yields only won rows mapped to (Segment, Category) over the minimal columns."""
    won = real_obs["won"]
    assert (won["Stage"] == WON).all()
    assert set(won.columns) <= {"OppId", "AccountId", "Stage", "Amount", "Segment", "Category"}
    assert won["Segment"].notna().all() and won["Category"].notna().all()


# --------------------------------------------------------------------------- #
# firewall
# --------------------------------------------------------------------------- #
def _recovery_sources():
    pkg = Path(__file__).resolve().parents[1]
    return {p.name: p.read_text(encoding="utf-8") for p in pkg.glob("*.py")}


def test_firewall_no_manifest_or_generator_reference():
    """INV-FW: the recovery package never reaches the manifest / generator / planted value."""
    for name, src in _recovery_sources().items():
        assert "ground_truth" not in src, f"{name} references the manifest"
        assert "_ground_truth" not in src, f"{name} references the manifest"
        assert not re.search(r"\bimport world_model\b|\bfrom world_model\b", src), \
            f"{name} imports the L0 generator"
        # the planted multiplier 3.2 as a numeric LITERAL (not a spec ref like "§3.2",
        # not part of 13.2 / 3.25 / 5.3.2)
        planted = [m.start() for m in re.finditer(r"3\.2", src)
                   if src[m.start() - 1] not in "§.0123456789"
                   and not src[m.end():m.end() + 1].isdigit()]
        assert not planted, f"{name} hard-codes the planted effect size 3.2"


def test_attestation_hash_matches_and_flag_false(real_obs, real_result):
    """INV-ATT: manifest_read=false and observation_hash reproduces; any byte change flips it."""
    card = _build(real_obs, real_result)
    assert card["provenance"]["manifest_read"] is False
    assert card["provenance"]["observation_hash"] == io.observation_hash(real_obs["acc"], real_obs["opp"])
    tampered = real_obs["dir"] / "acc_tampered.csv"
    tampered.write_text(real_obs["acc"].read_text() + "\n# x")
    assert io.observation_hash(tampered, real_obs["opp"]) != card["provenance"]["observation_hash"]


# --------------------------------------------------------------------------- #
# invariant
# --------------------------------------------------------------------------- #
def test_inv_cvx_beta_between_raw_and_zero():
    """INV-CVX: each shrunk effect is a convex pull of the raw effect toward 0."""
    w = synth_won(42)
    seg = pd.Categorical(w["Segment"]); cat = pd.Categorical(w["Category"])
    adj = _segment_adjusted(np.log(w["Amount"].to_numpy(float)),
                            seg.codes.astype(np.int64), len(seg.categories))
    eff = _category_effects(adj, cat.codes.astype(np.int64), len(cat.categories),
                            len(seg.categories), 1.0)
    lo = np.minimum(eff["raw"], 0) - 1e-9
    hi = np.maximum(eff["raw"], 0) + 1e-9
    assert np.all((eff["beta"] >= lo) & (eff["beta"] <= hi))


def test_inv_mon_shrink_weight_monotonic_in_count():
    """INV-MON: with σ²,τ² fixed, the shrink weight increases with n_c."""
    tau2, sig2 = 0.3, 1.0
    ns = np.array([1, 2, 5, 10, 50, 200], float)
    w = tau2 / (tau2 + sig2 / ns)
    assert np.all(np.diff(w) > 0)


def test_inv_scl_member_set_scale_invariant():
    """INV-SCL: scaling Amount by k leaves the wedge member set unchanged."""
    w = synth_won(42)
    r1 = recover(w, n_perm=300, n_bootstrap=0, seed=1)
    w2 = w.copy(); w2["Amount"] = w2["Amount"] * 1000.0
    r2 = recover(w2, n_perm=300, n_bootstrap=0, seed=1)
    assert set(r1.members) == set(r2.members)
    assert r1.inv_scl


@pytest.mark.parametrize("seed", SEEDS)
def test_inv_null_fpr_approx_alpha(seed):
    """INV-NULL: under Amount⊥category, the existence gate does not fire and the
    held-out false-positive rate stays near α."""
    r = recover(null_won(seed), n_perm=300, n_bootstrap=0, seed=seed)
    assert r.decision is False
    assert r.observed_fpr <= 0.12


@pytest.mark.parametrize("seed", SEEDS)
def test_inv_stb_bootstrap_membership_stable(seed):
    """INV-STB: the wedge member set is stable under bootstrap resampling."""
    r = recover(synth_won(seed), n_perm=250, n_bootstrap=80, seed=seed)
    assert r.jaccard_stability >= 0.8


# --------------------------------------------------------------------------- #
# guard (form, not value)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
def test_payoff_baseline_overfires_inference_does_not(seed):
    """§7.3 payoff: under the null, the L0 fixed-quantile baseline flags low-count
    noise cells while the null-calibrated inference gate does not fire."""
    w = null_won(seed)
    flags = bl.baseline_flags(w)["cells"]
    r = recover(w, n_perm=300, n_bootstrap=0, seed=seed)
    assert len(flags) >= 1, "baseline expected to over-fire on noise"
    assert r.decision is False, "inference must not fabricate a wedge under the null"


def test_null_threshold_stable_across_permutation_count():
    """§7.4: the null (1−α) threshold is stable as B grows (well-defined calibration)."""
    w = synth_won(42)
    t_lo = recover(w, n_perm=400, n_bootstrap=0, seed=3).null_threshold
    t_hi = recover(w, n_perm=1200, n_bootstrap=0, seed=3).null_threshold
    assert abs(t_lo - t_hi) <= 0.15 * (abs(t_hi) + 1e-6) + 0.05


def test_membership_is_quantile_based_not_currency():
    """Members are defined by count percentile, never a currency threshold —
    so every member is in the rare (≤ p_low) band regardless of scale."""
    r = recover(synth_won(7), n_perm=300, n_bootstrap=0, seed=7, p_low=0.5)
    # recovered low-count candidate sits in the rare half
    assert r.count_percentile <= 0.5


# --------------------------------------------------------------------------- #
# absence (§8.2)
# --------------------------------------------------------------------------- #
def test_absence_no_wedge_in_high_count(real_result):
    """No member sits in the high-count band."""
    assert real_result.absence_no_high_count


def test_absence_no_wedge_in_low_arpa(real_result):
    """No member is below the null-calibrated elevation threshold."""
    assert real_result.absence_no_low_arpa


def test_absence_no_fabrication_under_null(real_result):
    """Held-out FPR stays within α (+ margin) — no fabrication from noise."""
    assert real_result.observed_fpr <= real_result.alpha + 0.05


def test_absence_no_truth_leak_in_observation(real_obs):
    """No observed column name betrays a leaked truth/plant field."""
    ok, hits = io.audit_columns(real_obs["acc"], real_obs["opp"])
    assert ok, f"truth-like columns present: {hits}"


def test_absence_no_false_wedge_in_owner_region(real_obs):
    """The existence gate does not fire on the non-planted owner/region axes."""
    owner = io.load_axis_frame(real_obs["acc"], real_obs["opp"], "OwnerId")
    r_owner = recover(owner, category_col="Axis", segment_col="Segment",
                      n_perm=300, n_bootstrap=0, seed=42)
    assert r_owner.decision is False
    region = io.load_axis_frame(real_obs["acc"], real_obs["opp"], "Region")
    if region["Axis"].nunique() >= 6:
        assert recover(region, category_col="Axis", segment_col="Segment",
                       n_perm=300, n_bootstrap=0, seed=42).decision is False


# --------------------------------------------------------------------------- #
# quirk (reference-habit audit, §9)
# --------------------------------------------------------------------------- #
def test_quirk_light_tail_kurtosis(real_obs):
    """★ recon claimed light tails — verify empirically: log-Amount is not heavy-tailed."""
    y = np.log(real_obs["won"]["Amount"].to_numpy(float))
    z = (y - y.mean()) / y.std()
    excess_kurt = float((z ** 4).mean() - 3)
    assert excess_kurt < 2.0, f"unexpected heavy tail: excess kurtosis={excess_kurt:.2f}"


def test_quirk_amounts_rounded_to_hundreds(real_obs):
    """100-unit rounding present; recovery still produces finite, non-degenerate stats."""
    amt = real_obs["won"]["Amount"].to_numpy(float)
    assert np.allclose(amt % 100, 0)
    r = recover(real_obs["won"], n_perm=200, n_bootstrap=0, seed=1)
    assert np.isfinite(r.separation_statistic) and np.isfinite(r.null_threshold)


def test_quirk_amount_positive_above_floor(real_obs):
    """The (0.5+engagement) floor implies Amount strictly positive (log-safe)."""
    assert (real_obs["won"]["Amount"] > 0).all()


def test_quirk_null_distribution_nondegenerate():
    """Bounded support must not collapse the permutation null to a point."""
    w = synth_won(42)
    a = recover(w, n_perm=400, n_bootstrap=0, seed=1).null_threshold
    b = recover(w, n_perm=400, n_bootstrap=0, seed=2).null_threshold
    assert np.isfinite(a) and np.isfinite(b) and a > 0 and abs(a - b) > 0


def test_quirk_segment_confound_separates():
    """Wedge concentrated in the low-value segment is still separated by β
    (segment adjustment prevents α/β mixing)."""
    w = synth_won(42, wedge_seg_bias="S1")   # rare high-value cat dumped in cheapest segment
    r = recover(w, n_perm=400, n_bootstrap=0, seed=1)
    assert r.category_id == "C3" and r.shrunk_effect_logspace > 0


def test_quirk_singleton_category_strongly_shrunk():
    """A category with n_c=1 must not crash and must be shrunk hard toward 0."""
    w = synth_won(42)
    # force exactly one row to a fresh singleton category
    w = w.copy()
    w.loc[w.index[0], "Category"] = "C_single"
    seg = pd.Categorical(w["Segment"]); cat = pd.Categorical(w["Category"])
    eff = _category_effects(_segment_adjusted(np.log(w["Amount"].to_numpy(float)),
                                              seg.codes.astype(np.int64), len(seg.categories)),
                            cat.codes.astype(np.int64), len(cat.categories),
                            len(seg.categories), 1.0)
    i = list(cat.categories).index("C_single")
    assert eff["counts"][i] == 1
    assert abs(eff["beta"][i]) <= abs(eff["raw"][i]) + 1e-9   # shrunk toward 0


def test_quirk_transaction_vs_account_dedup_robustness(real_obs):
    """Account-dedup (one won per account) must not flip the existence decision."""
    won = real_obs["won"]
    base = recover(won, n_perm=400, n_bootstrap=0, seed=42).decision
    dedup = won.drop_duplicates(subset="AccountId", keep="first")
    ded = recover(dedup, n_perm=400, n_bootstrap=0, seed=42).decision
    assert base == ded


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #
def test_card_carries_no_forbidden_tokens(real_obs, real_result):
    """The card carries the firewall attestation and no manifest reference.
    (elevation_ratio is L1's *estimate* and may legitimately be ~3.2x — that is a
    recovered value, not a leak of the planted constant.)"""
    blob = json.dumps(_build(real_obs, real_result))
    assert "ground_truth" not in blob
    assert '"manifest_read": false' in blob
