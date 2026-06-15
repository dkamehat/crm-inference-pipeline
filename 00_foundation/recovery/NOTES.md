# Recovery (L1) — deferred items & ratified defaults

## Ratified defaults (spec §14 R1) — confirmed against the real observation
`S_min=6, α=0.05, B=1000, p_low=0.5, J_min=0.8` (+ `k_kappa=1.0` for κ=k·τ).
The V1 observation has **N=8 categories ≥ S_min=6**, so the defaults were kept
**unchanged** — no adjustment to real N was required.

## Method choices recorded (not in spec, decided in implementation)
- **Segment-adjusted category effect** is computed as an additive ANOVA-style
  decomposition (`adjusted = y − α_segment`, then category means of `adjusted`,
  sum-to-zero centered). Chosen over a full OLS solve because it is O(n) and the
  segment-adjusted residual is *invariant under category permutation*, which keeps
  the permutation null fast and exact. Equivalent to OLS for the additive model on
  balanced data; the rank/cell-shrink alternative is B-L1-1/§9 robustness.
- **κ = k_kappa · τ** (k_kappa=1.0): elevation reference is one population-σ of the
  category-effect distribution — scale-free, not a currency level (spec §7.2).
- **Held-out FPR**: `observed_fpr` is measured on a *second, independent*
  permutation batch against the already-calibrated threshold, so it is not
  tautologically α (spec §8.2 no-fabrication).
- **Bootstrap stability** holds the null-calibrated threshold fixed and resamples
  rows — it measures sampling variability of the estimate, not of the calibration.

## Deferred B items (spec §13.3)
- **B-L1-1**: price estimator sensitivity (mean / trimmed / log-posterior).
- **B-L1-2**: generalize to multiple wedges (current method assumes a single
  category; membership can return a set, but the existence statistic targets the
  top low-count mode).
- **B-L1-3**: swap the separation statistic T (gap-based) for a
  mixture-improvement statistic and compare.
- **B-L1-4**: post_prob calibration measurement is L3's to define (sent to L3).
- **B-L1-5**: transaction vs account dedup — first-class definition is currently
  transaction-grain (L0 parity, R3); dedup runs only as a robustness check.

## Temperature notes (from L0 recon)
- **Season smear is irrelevant to the wedge**: the wedge is recovered over the
  whole horizon (no time slicing), so the L0 "recorded close month ±1 drift" note
  does not affect this layer.
- **Guard size-dependence (L0 limitation) is what L1 improves on**: L1 thresholds
  are quantile / null-calibrated to be scale- and size-robust, but below `S_min`
  the null itself is unstable — the `S_min` precondition guards that boundary.
