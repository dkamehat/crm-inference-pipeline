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

## B — auto-close interaction at long horizons
The days-open cap (`stage_lag_cap_days`) auto-closes the open tail as lost. In
the 18-period thin slice this is effectively inert (the window bounds days-open
on its own); it only fires for longer runs.

- **Watch:** at long horizons, auto-closing the high-potential *under-covered*
  backlog could begin to erode the coverage confound (signal ⑨), since those
  opps would convert from "open/under-covered" to "closed-lost". Revisit the cap
  vs. coverage-signal interaction when extending beyond the thin slice.
