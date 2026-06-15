# Grading (L3) — scope, pending items, hand-offs

## v1 scope (implemented)
Decision-gated TP / FP / FN (spec §4.1) + magnitude calibration (§5.1) + firewall
re-verification (§4.4), aggregated over a set of (manifest, card) pairs.

## Pending / deferred (clean extension points, not stubbed)
- **TN — pending no-wedge profile (hand-off §8.1).** The V1 generator plants a
  wedge unconditionally, so no manifest-graded TN instances exist. The aggregator
  reports `TN: "pending no-wedge profile"`. Closing this needs an *additive*
  no-wedge L0 profile (`wedge: null` / flat `cat_value_mult`) — L3 must not modify
  L0, so it is a hand-off. L1's card-side absence checks are self-attestations, not
  manifest-graded TN, and do not substitute.
- **post_prob calibration §5.2 — deferred (hand-off §8.2).** The card exposes
  `post_prob_elevated` only for the single recovered wedge, not per category, so a
  reliability curve has no negatives to bin. Enable when the card exposes
  per-category posteriors (or a no-wedge profile supplies negatives), and pin θ in
  `truth_elevated(cat) := cat_value_mult[cat] > θ` to L1's "elevated" definition.

## Method choices
- **Magnitude calibration is over TP instances only.** elevation_ratio estimates
  the planted magnitude only when the recovered category equals the planted one;
  on an FP the estimate is for a different category, so comparing it to planted_mag
  is meaningless. Bias is reported (mean + dispersion), never asserted to be zero.
- **Like-for-like reference frame (corrected).** L1's `elevation_ratio` is
  geomean-relative: `exp(β)` with β sum-to-zero centered in log space, i.e. the
  wedge category's value relative to the geomean of all category multipliers. The
  ABSOLUTE multiplier `cat_value_mult[planted_cat]` is unidentifiable under that
  centering, so the calibration target is
  `cat_value_mult[planted_cat] / geomean(all cat_value_mult)`. Measured this way the
  bias is **near zero** (≈unbiased on the 50-seed set); EB attenuation is negligible
  at this evidence strength. The earlier "downward ~10%" was a **reference-frame
  artifact** (the wedge's own multiplier pulls the geomean above 1.0) — it is
  reported separately and explicitly labeled `..._offset_not_a_bias`, never as the
  bias.
- **Observation hash is replicated, not imported.** `provenance.observation_hash`
  re-implements the L1 spec's hash (sha256 over the two path-sorted observed CSVs)
  as a pure primitive, so L3 audits the firewall without importing recovery logic.

## Input dependency (not L3's to build)
The aggregate needs persisted multi-seed (manifest, card) pairs. Generating them
requires running L1 (forbidden here). They must come from an L1/orchestration-lane
harness that, per seed, emits the observation (L0) + the card (L1) into a subdir.
Until that exists, `run.py` grades the single sample pair as a smoke test and flags
the gap.
