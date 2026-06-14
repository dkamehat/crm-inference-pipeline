# WorldModel — deferred items (B backlog)

Decisions consciously deferred from the V1 thin slice. Nothing is dropped
silently — each item records why it is safe to defer and when to revisit.

## B — emit-layer idempotency via a derived rng
`emit()` draws the record-layer distortions (stage-lag, happy-ears,
close-optimism, observed controlling-entity) from the shared `WorldModel.rng`
*after* `simulate()`. This means calling `emit()` twice on the *same* instance
would advance the rng and produce different output the second time.

- **Impact today:** none. Output is fully reproducible across fresh runs (the
  seed-reproducibility test is green), and nothing calls `emit()` twice on one
  instance. Not on the G1 critical path.
- **Fix when revisited:** give the emit layer its own rng derived from the seed
  (e.g. `random.Random(seed ^ EMIT_SALT)`), so emit is pure/idempotent and
  independent of simulate's rng consumption.

## B — profile-driven self_check (for V2/V3)
`self_check` hardcodes a few V1-specific strings (segment names `SMB`/
`Enterprise`, loss reasons `Price`/`No Decision`) in the segment-conditional
loss check.

- **Impact today:** none — these are correct for V1.
- **Fix when revisited:** when V2 lands, drive those expectations from the
  profile / manifest instead of literals, so one harness serves every profile.

## B — PDCA should learn from the realized rate, not nudge toward true directly
`AssumedScoreModel.pdca_update` nudges the assumed category weight toward the
hidden `true_cat_w` directly (gated on `tot >= 5` as a "enough signal" proxy),
rather than toward the *realized* win-rate-by-category computed from the data.

- **Impact today:** correct for the thin slice — with `overfit_pull = 0` the world
  converges cleanly, which is what V1 wants. But it means signal ⑩ (weight-gap
  convergence) is partly *by construction* rather than learned from observed
  outcomes, so it is a weaker demonstration of "learning from data".
- **Fix when revisited:** when `overfit_pull` is enabled (B), drive the update
  from the realized win-rate-by-category (with noise/vanity-signal following), so
  convergence — and the over-fitting failure mode — emerge from the data.

## L1 note — recorded close month may drift +/-1 (day-level approximation)
The recorded close date is reconstructed at day granularity as
`created + months_gap*30 + within_offset - bounded_optimism`. Because months are
approximated as 30 days (plus the within-month jitter and optimism), the recorded
close *month* can drift by about +/-1 from the recorded close *period*.

- **Not a bug** — a deliberate day-level realism approximation (it removed the
  0-day / 1-day close pile-ups). It does mean the planted seasonality is very
  slightly smeared in the observed data vs. the exact first-of-month it used to
  carry. Signal (1) still recovers (CV ~0.31).
- **For L1:** when recovering seasonality, expect a small amount of month
  smearing; aggregate at the quarter level or smooth if a sharper read is needed.

## Known limitation — activities have no temporal spread (Phase-4 hand-off)
Every activity is dated on its opp's `CreatedDate` (no spread across the deal's
life). In V1 this is harmless — no planted signal or integrity check reads
`ActivityDate` — so it is a deliberate thin-slice simplification, NOT a bug.

- **For whoever builds activity-based analysis (Phase 4: lead scoring on
  Opportunities x Activities):** activities will all cluster at creation. Spread
  them over the deal's life (created..close) before using activity *timing* as a
  feature. Logged here so it is not rediscovered as a "bug".

## Known limitation — integrity/dwell guard thresholds are population-size dependent
The dwell and integrity guards use fixed shares (dwell: <=2d <15% and single
day-value <10%; integrity: owner <25%, category <20%). These are calibrated for
the default / CI population (n_accounts=1200, t_periods=18).

- **Impact:** a much smaller run (e.g. `--accounts 50`) produces a sparse
  distribution where a single value can legitimately exceed a threshold — a false
  positive, not a real regression. Correct for the default and CI configs.
- **If small runs become a use case:** scale the thresholds by population size (or
  switch to a relative "< k x equal-share" form). See the comments at the guard
  sites in `self_check.run_integrity_checks` and check ④.

## B — auto-close interaction at long horizons
The days-open cap (`stage_lag_cap_days`) auto-closes the open tail as lost. In
the 18-period thin slice this is effectively inert (the window bounds days-open
on its own); it only fires for longer runs.

- **Watch:** at long horizons, auto-closing the high-potential *under-covered*
  backlog could begin to erode the coverage confound (signal ⑨), since those
  opps would convert from "open/under-covered" to "closed-lost". Revisit the cap
  vs. coverage-signal interaction when extending beyond the thin slice.
