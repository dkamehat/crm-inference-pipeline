"""
Distribution-shape guards (spec §7): thresholds come from the null's shape, not
from hand-placed currency values. The wedge "exists?" decision and the membership
elevation threshold are both calibrated against a permutation null in which the
category labels are shuffled (Amount independent of category).

This module is generic and statistic-agnostic: it knows nothing about the wedge.
It supplies the permutation engine, the null-quantile threshold, the p-value, the
Jaccard helper for bootstrap stability, and the normal survival function used for
posterior elevation probabilities.
"""

from __future__ import annotations

import math

import numpy as np

_SQRT2 = math.sqrt(2.0)


def norm_sf(z) -> np.ndarray:
    """Survival function P(Z > z) for the standard normal, vectorized via erfc."""
    z = np.atleast_1d(np.asarray(z, dtype=float))
    return np.array([0.5 * math.erfc(zi / _SQRT2) for zi in z])


def kappa_from_tau(tau2: float, k_kappa: float) -> float:
    """Elevation reference κ derived from the category-effect spread, not a fixed
    currency level (spec §7.2): κ = k_kappa · τ. Scale-invariant in log space."""
    return k_kappa * math.sqrt(max(tau2, 0.0))


def permute_statistics(stat_fn, cat_codes: np.ndarray, n_perm: int,
                       rng: np.random.Generator) -> np.ndarray:
    """Shuffle the category labels n_perm times (Amount ⊥ category) and collect
    stat_fn(permuted_codes). Returns shape (n_perm, k). Permuting the label vector
    preserves each category's count exactly — only the Amount↔category link breaks,
    which is the null the existence gate is calibrated against (spec §5.3)."""
    rows = []
    for _ in range(n_perm):
        rows.append(stat_fn(rng.permutation(cat_codes)))
    return np.asarray(rows, dtype=float)


def null_threshold(null_values: np.ndarray, alpha: float) -> float:
    """(1−α) quantile of a null statistic distribution."""
    return float(np.quantile(null_values, 1.0 - alpha))


def p_value(null_values: np.ndarray, observed: float) -> float:
    """Right-tailed permutation p-value with the +1 correction."""
    n = len(null_values)
    return float((1 + int(np.sum(null_values >= observed))) / (n + 1))


def jaccard(a: set, b: set) -> float:
    """Jaccard similarity; two empty sets count as identical (1.0)."""
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 1.0
