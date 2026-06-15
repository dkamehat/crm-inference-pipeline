"""
Wedge inference (spec §5): recover the value-concentration blind-spot from the
observation alone — distinguish "a category that is genuinely high-value but small"
from "a small category that looks high by sampling noise".

Method (spec §5.2): work in log space (the generative drivers are multiplicative,
so log makes them additive — spec §5.1). Fit an additive two-way decomposition
log(Amount) = μ + α_segment + β_category + ε, then empirical-Bayes shrink each
β_category toward 0 with weight τ²/(τ² + σ²/n_c). Small categories shrink hard, so
a category that survives shrinkage is genuinely elevated. Existence and membership
thresholds are calibrated against a permutation null (spec §5.3/§5.4, guards.py),
never against fixed currency values or the planted effect size (firewall, §0.3).

Nothing here reads the manifest or the generator — only the passed observation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import guards


@dataclass
class RecoveryResult:
    # provenance-ish
    n_won: int
    value_field: str
    log_delta: float
    n_perm: int
    alpha: float
    # existence gate (spec §5.3)
    decision: bool
    separation_statistic: float
    null_threshold: float
    p_value_vs_null: float
    # recovered claim (spec §5.2) — the strongest low-count elevated category
    category_id: str
    rec_n_won: int
    count_percentile: float
    raw_arpa: float
    shrunk_effect_logspace: float
    elevation_ratio: float
    post_prob_elevated: float
    cell_breakdown: list
    # membership + self-attested health
    members: list
    absence_no_high_count: bool
    absence_no_low_arpa: bool
    observed_fpr: float
    inv_cvx: bool
    inv_mon: bool
    inv_scl: bool
    inv_null: bool
    inv_stb: bool
    jaccard_stability: float


def _segment_adjusted(y: np.ndarray, seg_codes: np.ndarray, n_seg: int) -> np.ndarray:
    """Remove the segment level from log-value (controls for segment composition).
    Independent of the category labels, so it is stable across category permutations."""
    mu_y = y.mean()
    seg_cnt = np.bincount(seg_codes, minlength=n_seg).astype(float)
    seg_sum = np.bincount(seg_codes, weights=y, minlength=n_seg)
    seg_mean = seg_sum / np.maximum(seg_cnt, 1)
    alpha_s = seg_mean - mu_y
    return y - alpha_s[seg_codes]


def _category_effects(adjusted: np.ndarray, cat_codes: np.ndarray,
                      n_cat: int, n_seg: int, k_kappa: float) -> dict:
    """Empirical-Bayes category effects on segment-adjusted log-value (spec §5.2).

    Categories ABSENT from the data (count==0, e.g. dropped by a bootstrap resample)
    are excluded — they get no effect (NaN), are not centered into the population,
    and never become members. When all categories are present (the main path) this is
    bit-identical to the unmasked computation (no regression)."""
    n = len(adjusted)
    counts = np.bincount(cat_codes, minlength=n_cat).astype(float)
    present = counts > 0
    safe = np.where(present, counts, 1.0)
    sums = np.bincount(cat_codes, weights=adjusted, minlength=n_cat)
    mu = float(adjusted.mean())
    raw = np.where(present, sums / safe - mu, np.nan)
    raw = raw - np.nanmean(raw)                  # sum-to-zero over PRESENT categories
    resid = adjusted - mu - np.nan_to_num(raw)[cat_codes]   # cat_codes only index present
    p = (n_seg - 1) + (n_cat - 1) + 1
    sigma2 = float((resid ** 2).sum()) / max(1, n - p)
    n_present = int(present.sum())
    var_raw = float(np.nanvar(raw, ddof=1)) if n_present > 1 else 0.0
    tau2 = max(0.0, var_raw - float(np.mean((sigma2 / safe)[present])))   # method-of-moments
    w = np.where(present, tau2 / (tau2 + sigma2 / safe), np.nan)  # shrink weight in [0, 1]
    beta = w * raw                               # INV-CVX: between 0 and raw
    post_var = np.where(present, w * sigma2 / safe, np.nan)       # EB posterior variance
    kappa = guards.kappa_from_tau(tau2, k_kappa)
    post_prob = np.zeros(n_cat)                  # absent -> 0 (never elevated)
    pos = present & (post_var > 0)
    if pos.any():
        z = (kappa - beta[pos]) / np.sqrt(post_var[pos])
        post_prob[pos] = guards.norm_sf(z)
    return dict(counts=counts, raw=raw, beta=beta, post_var=post_var, present=present,
                sigma2=sigma2, tau2=tau2, w=w, post_prob=post_prob, kappa=kappa)


def _separation_T(beta: np.ndarray, low_mask: np.ndarray) -> float:
    """Separation of the most-elevated low-count category from the bulk (spec §5.3)."""
    if not low_mask.any():
        return float("-inf")
    return float(beta[low_mask].max() - np.median(beta))


def _count_percentile(counts: np.ndarray) -> np.ndarray:
    """Mid-rank percentile of each category's count (smaller = rarer)."""
    n = len(counts)
    less = (counts[None, :] < counts[:, None]).sum(1)
    equal = (counts[None, :] == counts[:, None]).sum(1)
    return (less + 0.5 * equal) / n


def _count_percentile_present(counts: np.ndarray) -> np.ndarray:
    """Count percentile computed over PRESENT categories only (absent -> +inf, so
    they are never rare-enough to be members). Identical to _count_percentile when
    all categories are present."""
    present = counts > 0
    out = np.full(len(counts), np.inf)
    c = counts[present]
    if len(c):
        less = (c[None, :] < c[:, None]).sum(1)
        equal = (c[None, :] == c[:, None]).sum(1)
        out[present] = (less + 0.5 * equal) / len(c)
    return out


def recover(df: pd.DataFrame, *, category_col: str = "Category",
            segment_col: str = "Segment", value_col: str = "Amount",
            alpha: float = 0.05, n_perm: int = 1000, p_low: float = 0.5,
            j_min: float = 0.8, k_kappa: float = 1.0, n_bootstrap: int = 200,
            log_delta: float = 0.0, seed: int = 0) -> RecoveryResult:
    """Run the full wedge inference and return a falsifiable result (spec §5.6).
    L1 does NOT decide whether recovery is correct — that is L3's job."""
    rng = np.random.default_rng(seed)

    seg = pd.Categorical(df[segment_col])
    cat = pd.Categorical(df[category_col])
    seg_codes = seg.codes.astype(np.int64)
    cat_codes = cat.codes.astype(np.int64)
    cat_labels = list(cat.categories)
    n_seg, n_cat = len(seg.categories), len(cat_labels)

    amount = df[value_col].to_numpy(dtype=float)
    y = np.log(amount + log_delta) if log_delta else np.log(amount)
    adjusted = _segment_adjusted(y, seg_codes, n_seg)

    eff = _category_effects(adjusted, cat_codes, n_cat, n_seg, k_kappa)
    counts = eff["counts"]
    low_mask = counts <= np.quantile(counts, 1.0 / 3.0)   # bottom tercile (spec §5.3)
    T_obs = _separation_T(eff["beta"], low_mask)

    # permutation null: shuffle category labels (Amount ⊥ category) (spec §5.3)
    def stat(perm_codes):
        e = _category_effects(adjusted, perm_codes, n_cat, n_seg, k_kappa)
        pp = e["post_prob"][low_mask].max() if low_mask.any() else 0.0
        return (_separation_T(e["beta"], low_mask), pp)

    null = guards.permute_statistics(stat, cat_codes, n_perm, rng)
    T_null, pp_null = null[:, 0], null[:, 1]
    null_thr = guards.null_threshold(T_null, alpha)
    decision = bool(T_obs > null_thr)
    p_val = guards.p_value(T_null, T_obs)
    thr_elev = guards.null_threshold(pp_null, alpha)     # null-calibrated membership thr (§5.4)

    # membership: rare (count percentile) AND elevated (post_prob over null thr)
    count_pct = _count_percentile(counts)
    member_mask = (count_pct <= p_low) & (eff["post_prob"] >= thr_elev)
    members = [cat_labels[i] for i in np.where(member_mask)[0]]

    # recovered claim = strongest low-count elevated category (falsifiable either way)
    cand = np.where(low_mask)[0]
    rec_i = int(cand[np.argmax(eff["beta"][cand])]) if len(cand) else int(np.argmax(eff["beta"]))
    rec_label = cat_labels[rec_i]

    # category- and cell-level ARPA for the card
    df_cat = df[cat_codes == rec_i]
    raw_arpa = float(df_cat[value_col].mean())
    cell_breakdown = [
        {"segment_id": str(s), "n_won": int(len(g)), "raw_arpa": float(g[value_col].mean())}
        for s, g in df_cat.groupby(segment_col, observed=True)
    ]

    # held-out FPR attestation (independent perm batch vs the calibrated threshold)
    null2 = guards.permute_statistics(stat, cat_codes, n_perm, rng)
    observed_fpr = float(np.mean(null2[:, 0] > null_thr))

    # INV-CVX: beta is a convex pull of raw toward 0
    inv_cvx = bool(np.all((eff["beta"] >= np.minimum(eff["raw"], 0) - 1e-9) &
                          (eff["beta"] <= np.maximum(eff["raw"], 0) + 1e-9)))
    # INV-MON: shrink weight non-decreasing in count
    order = np.argsort(counts)
    inv_mon = bool(np.all(np.diff(eff["w"][order]) >= -1e-9))
    # INV-NULL: held-out firing rate ≈ alpha
    inv_null = bool(observed_fpr <= alpha + 0.05)

    # INV-SCL: Amount × k leaves the member set unchanged (log adds a constant)
    k = 1000.0
    adj_scaled = adjusted + np.log(k)
    eff_s = _category_effects(adj_scaled, cat_codes, n_cat, n_seg, k_kappa)
    mem_s = {cat_labels[i] for i in np.where(
        (count_pct <= p_low) & (eff_s["post_prob"] >= thr_elev))[0]}
    inv_scl = bool(mem_s == set(members))

    # INV-STB: bootstrap stability of the member set (Jaccard >= j_min)
    jac = _bootstrap_jaccard(y, seg_codes, cat_codes, n_seg, n_cat, k_kappa,
                             cat_labels, thr_elev, p_low, set(members),
                             n_bootstrap, rng)
    inv_stb = bool(jac >= j_min)

    return RecoveryResult(
        n_won=int(len(df)), value_field=value_col, log_delta=float(log_delta),
        n_perm=int(n_perm), alpha=float(alpha),
        decision=decision, separation_statistic=float(T_obs),
        null_threshold=float(null_thr), p_value_vs_null=float(p_val),
        category_id=str(rec_label), rec_n_won=int(counts[rec_i]),
        count_percentile=float(count_pct[rec_i]), raw_arpa=raw_arpa,
        shrunk_effect_logspace=float(eff["beta"][rec_i]),
        elevation_ratio=float(np.exp(eff["beta"][rec_i])),
        post_prob_elevated=float(eff["post_prob"][rec_i]),
        cell_breakdown=cell_breakdown, members=members,
        absence_no_high_count=bool(not np.any(member_mask & (count_pct > p_low))),
        absence_no_low_arpa=bool(not np.any(member_mask & (eff["post_prob"] < thr_elev))),
        observed_fpr=observed_fpr,
        inv_cvx=inv_cvx, inv_mon=inv_mon, inv_scl=inv_scl, inv_null=inv_null,
        inv_stb=inv_stb, jaccard_stability=float(jac),
    )


def _bootstrap_jaccard(y, seg_codes, cat_codes, n_seg, n_cat, k_kappa,
                       cat_labels, thr_elev, p_low, members, n_boot, rng) -> float:
    """Resample won rows with replacement; recompute the member set under the
    already-calibrated threshold; report mean Jaccard vs the observed set (INV-STB).
    Holds the null-calibrated threshold fixed (measures sampling variability of the
    estimate, not of the calibration)."""
    if n_boot <= 0:
        return 1.0
    n = len(y)
    jacs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        adj_b = _segment_adjusted(y[idx], seg_codes[idx], n_seg)
        eff_b = _category_effects(adj_b, cat_codes[idx], n_cat, n_seg, k_kappa)
        present = eff_b["counts"] > 0
        cpct_b = _count_percentile_present(eff_b["counts"])
        mem_b = {cat_labels[i] for i in np.where(
            present & (cpct_b <= p_low) & (eff_b["post_prob"] >= thr_elev))[0]}
        # evaluate stability over categories present in this resample (spec §6 INV-STB):
        # a category absent from the resample is "no data here", not evidence either way.
        present_labels = {cat_labels[i] for i in np.where(present)[0]}
        jacs.append(guards.jaccard(members & present_labels, mem_b))
    return float(np.mean(jacs))
