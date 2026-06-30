# Decision (L2) — design choices & deferred items

## Method choices recorded (decided in implementation)
- **Single sortable score, not a multi-pass sort.** The three keys are folded into
  one descending score with lexicographic weights (`W1=1000 ≫ W2·max_tier=30 ≫
  W3·max(1/(1+n_won))=1`). This is equivalent to a stable multi-key sort but makes
  the score auditable as a single number per account. The W values are an
  implementation detail (spec §4.2 fixes only key priority + determinism).
- **Penetration = Closed-Won count, never total Amount.** Amount is populated on Won
  AND Lost opps (open = 0), so a value-weighted count would conflate wins with
  losses. Realized penetration is Won-only (spec §4.1).
- **Deterministic tie-break by AccountId.** Same (category, tier, n_won) ties resolve
  by AccountId ascending, so the ranking is reproducible regardless of input row
  order (verified in `test_rank_deterministic_tiebreak_by_account_id`).
- **Unknown segment label → tier 0.** A label outside {Enterprise, MidMarket, SMB}
  is ranked last within its block rather than crashing — defensive for future
  profiles with new segments.

## Firewall — same attestation as L1
The ranking carries `provenance.manifest_read=false` and an `observation_hash`
computed identically to L1's (`recovery.io` / `grading.provenance`). L3 re-verifies
both layers with the **same** `firewall.reverify` (the ranking and the card share the
provenance shape) — one verifier audits L1 and L2. A ranking that fails is rejected,
never graded (spec §6, verified in `test_grade_dirs_rejects_*`).

## Grading scope — what precision@K (Option A) certifies
- **Certifies:** L2 pulled the planted high-value population to the top out of the
  full universe (pass = precision@K ≫ base rate). The full-universe contract is what
  gives the metric meaning — a pre-filtered candidate set would make it 1.0 by
  construction, measuring nothing (`test_..._answer_ignoring_ranker_collapses_to_base_rate`).
- **Does not certify:** the within-block ordering (keys 2–3). Option A treats all
  positives as equal — see the deferred Option B below.

## Deferred items
- **Option B — within-category value ordering.** Needs a per-account true latent
  value field the manifest does not emit. Deferred to an additive L0 extension
  (emit each account's true value / its components), after which L3 can grade a
  true-value precision@K or NDCG that scores keys 2–3. Additive only — existing L0
  output stays byte-identical (spec §7). Until it lands, v1 grades Option A only.
- **No-wedge / TN profile.** V1 always plants a wedge, so there is no
  decision-should-be-empty instance for L2 either. When the no-wedge profile lands
  (shared with the L1/L3 TN hand-off), L2 should produce a ranking with no dominant
  category block and precision@K should collapse to the base rate.
- **Card-weighted ordering (optional).** A future L2 could weight within-block order
  by the card's per-segment `cell_breakdown` strength; the field is already present,
  so no card-schema change is needed (spec §7).

## Why the segment-order caveat is stated, not silently assumed
`seg_value_mult` (SMB 0.4 < MidMarket 1.0 < Enterprise 2.6) is a non-emitted profile
constant. L2 cannot read it without breaking the firewall, so the Enterprise >
MidMarket > SMB tiering is an **observable assumption on the label order**, flagged
in `rank.py` and the spec (§4.1) — consistent with the project's "measure what you
can verify; flag what you can't" discipline.
