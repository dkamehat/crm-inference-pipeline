# L2-DECISION-SPEC.md — Account Prioritization Decision Layer (v0.1)

## 0. Purpose

L1 recovers *where* the hidden value is (a category, under a firewall, with a
calibrated false-positive rate). L2 turns that recovery into a **decision**:
given the recovered high-value / low-conversion category, **rank the full
account universe** so a sales team knows *which accounts to work next*.

This is the "drive the business" leg. L1 answers "what did we miss?"; L2 answers
"what do we do about it?"; L3 (extended) answers "was that decision sound?" —
graded against ground truth.

The decision target is the population a conversion-weighted view deprioritizes
but a value-weighted view should pursue: accounts in the recovered category
(high value `cat_value_mult`≈3.2 — the raw absolute multiplier; the repo README
reports the same wedge as ~2.8× on a geomean-relative, like-for-like basis), low
conversion `true_cat_w`≈−0.55) that are still under-penetrated.

## 1. Scope (v1) and non-scope

**In scope (v1):**
- A deterministic L2 ranker: `(L1 card, observed accounts, observed
  opportunities) → ranked list of all AccountIds with scores`.
- An L3 decision-grading mode: `precision@K` of the ranked list against the
  ground-truth high-value population (Option A — category membership).

**Explicitly not in scope (v1), handed off:**
- Grading the *within-category* ordering quality (whether L2 ordered the wedge
  accounts by true per-account value). This needs a per-account latent-value
  field the manifest does not emit — **Option B**, deferred to an additive L0
  extension (§7). v1 does not claim to measure it.

## 2. Firewall partition (4 layers — unchanged invariant)

L2 inherits the same firewall discipline as L1. **Only L3 reads the answer.**

| Layer | Reads | Writes | Answer access |
|---|---|---|---|
| L0 world model | profile/seed | observations + sealed ground truth | **writes** the answer |
| L1 recovery | observations only | recovery card | **none** |
| **L2 decision** | **observations + L1 card** | **ranked account list** | **none** |
| L3 grading | card + L2 output + ground truth | grade report | **reads** (sole reader) |

L2's inputs are exactly: `data/v1/accounts.csv`, `data/v1/opportunities.csv`
(observable), and the L1 recovery card (recovered category + per-segment
cell_breakdown). **L2 must not read `_ground_truth.json` or any manifest
path.** This is enforced the same way as L1's manifest-non-reference: a static
check (no manifest path in L2 source) plus L3 re-verification of provenance.

## 3. L2 input / output contract

### Input
- **L1 card**: provides `recovered_wedge_category.category_id` (e.g. `Cat-D`)
  and per-segment `cell_breakdown`. v1 uses only the recovered category_id; the
  cell_breakdown is available but not required by the v1 score.
- **accounts.csv**: `AccountId` (unique string), `Segment`
  (Enterprise/MidMarket/SMB), `Category`, `Region`, `ControllingEntityId`,
  `CreatedDate`. 1200 rows.
- **opportunities.csv**: `OppId`, `AccountId`, `Stage`, `Amount`, `Source`,
  `OwnerId`, `CreatedDate`, `CloseDate`, `LossReason`.

### Output
A ranked list covering the **entire account universe** (all 1200 accounts),
each row: `{ AccountId, rank, score, in_recovered_category: bool,
segment_tier: int, n_won: int }`. Ranking the full universe — not a
wedge-category pre-filter — is mandatory; see §5 (it is what makes grading
non-trivial).

## 4. Decision logic — the L2 score

### 4.1 Observable features (firewall-safe)

All derived from observations only:

- **`in_recovered_category`** (primary signal): `accounts.Category ==
  card.recovered_wedge_category.category_id`. This is L2 *using* L1's recovery —
  the whole point.
- **`segment_tier`** (value proxy): ordinal map from the observable Segment
  label — `Enterprise → 3, MidMarket → 2, SMB → 1`.
  ⚠ **Assumption, not verified:** the order Enterprise > MidMarket > SMB matches
  true value (design intent: seg_value_mult 2.6 > 1.0 > 0.4), but
  seg_value_mult is a non-emitted profile constant — L2 cannot confirm it
  read-only. v1 treats the label order as a stated observable assumption.
- **`n_won`** (penetration): count of that account's opportunities with
  `Stage == "06 - Closed Won"`. **Under-penetration = low `n_won`.**
  ⚠ Do **not** use total `Amount` for penetration: Amount is populated on both
  Won and Lost opps (open = 0), so total Amount conflates wins with losses.
  Realized penetration is Won-only.

### 4.2 Scoring — hierarchical, deterministic

The score orders accounts by three keys, in priority order:

1. **Category match** (primary): `in_recovered_category` accounts rank above all
   non-category accounts. This block boundary is the decision — "pursue the
   recovered category."
2. **Segment tier** (secondary): within a category block, higher tier first
   (Ent > MM > SMB) — the observable value proxy.
3. **Under-penetration** (tertiary): within the same tier, fewer `n_won` first —
   the "high value, still not worked" accounts surface to the top.

Concretely, a single sortable score (descending), with weights chosen so the
keys are lexicographic (category dominates tier dominates penetration):

```
score = W1 * 1[in_recovered_category]
      + W2 * segment_tier
      + W3 * (1 / (1 + n_won))
with W1 >> W2 * max_tier >> W3 * max(1/(1+n_won))   # e.g. W1=1000, W2=10, W3=1
```

Lexicographic-by-construction: no tuning sensitivity — the weights only need to
preserve key priority, not be calibrated. Ties (same category/tier/n_won) broken
deterministically by `AccountId` (stable, reproducible). The exact W values are
an implementation detail; the spec fixes only the **key priority** and that the
ordering is deterministic.

### 4.3 What the score deliberately does *not* do (v1)
It does not estimate each account's true monetary value — it has no
firewall-safe way to (seg_value_mult, value_base, per-account engagement are all
unobservable). The within-category ordering (keys 2–3) is a *reasonable
business heuristic*, and its correctness against true value is an Option-B
measurement, not claimed here.

## 5. L3 decision-grading mode — precision@K (Option A)

### 5.1 Ground-truth positive set
L3 (the sole answer-reader) builds the positive set from the manifest:
`positives = { AccountId : accounts.Category == manifest.wedge.category }`
— the planted high-value × low-conversion population. On the reference world:
**157 of 1200 accounts (base rate ≈ 13%)**, spanning all segments (anchor
MidMarket 47, plus SMB 101, Enterprise 9).

### 5.2 Metric
`precision@K = |topK(L2 ranking) ∩ positives| / K`, computed over the
full-universe ranking and averaged across a multi-seed set (same harness pattern
as recovery grading) → mean precision@K.

*Implementation dependency:* the current harness emits only the quad
(manifest / card / accounts / opps); Option-A grading additionally requires a
per-seed L2 ranking. The harness must therefore be extended to run L2 on each
seed and emit its ranking alongside the quad. (Tracked in §7.)

### 5.3 What K is, and how to read it
**K is the size of the action shortlist** — "if the sales team can only work the
top K accounts this cycle, how many of those K are genuinely in the
high-value population?" precision@K is therefore a *decision-relevant* metric,
not an abstract score: it answers "of the accounts L2 told you to pursue first,
what fraction were right?"

Because K models a real capacity constraint, the spec reports a **K sweep**
rather than a single number, since the right K depends on the team's bandwidth:

| K | What it asks | Interpretation on the reference world (157 positives) |
|---|---|---|
| 10 | the very top of the list | strictest; tiny shortlist must be near-perfect |
| 50 (default) | a realistic one-cycle shortlist | headline number; 50 ≤ 157 so a correct L2 can reach ~1.0 |
| 100 | a larger campaign list | still ≤ 157, so a correct L2 stays high |
| 157 | exactly the positive-set size | the natural ceiling — at K = |positives|, perfect recall and precision coincide |
| 200 | beyond the positive set | precision must fall (only 157 positives exist) — sanity check that the metric behaves |

**Default headline K = 50.** It sits well below the 157 positives (so a correct
ranker is not capped) and reflects a plausible "accounts a team works in one
cycle." Reporting the sweep makes the metric honest: it shows the number is not
an artifact of one convenient K, and the K = 200 row confirms precision degrades
once the shortlist exceeds the true population (a correctness check on the
metric itself).

### 5.4 Pass signal — and why the full-universe rule matters
- If L2 **ignores** the recovered category, top-K is a random draw → precision@K
  ≈ the 13% base rate.
- If L2 **correctly uses** the recovered category, the wedge-category block fills
  the top (157 ≥ K for K ≤ 157) → precision@K ≈ **1.0**.
- **Pass = precision@K ≫ base rate** (e.g. ≥ 0.9 at K = 50 vs 0.13). This is a
  real test *only because L2 ranks all 1200 accounts.* 🟠 If L2 were given only
  wedge-category accounts as candidates, top-K ⊆ Cat-D trivially ⇒ precision@K =
  1.0 by construction, measuring nothing. The full-universe contract (§3) is
  what gives the metric meaning: it verifies L2 *discriminated* the wedge
  category out of the whole population.

### 5.5 What precision@K (Option A) does and does not certify
- **Certifies:** L2 correctly translated L1's recovered category into account
  prioritization — it pulled the planted high-value population to the top out of
  the full universe.
- **Does not certify:** the *ordering within* the wedge-category block (score
  keys 2–3, segment-tier + under-penetration). Option A treats all 157 positives
  as equal, so that ordering is invisible to it. Measuring it requires true
  per-account value (Option B, §7). v1 states this limitation rather than
  implying the score's internal ordering is validated.

**Attribution note.** Strictly, precision@K grades the *composed* L1→L2 decision
against truth: L2 ranks by the card's *recovered* category, while L3 scores
against the manifest's *true planted* category, so a seed where L1 mis-recovers
would lower precision@K even with a perfect L2. On the reference world this
isolates L2 in practice because L1 recovery runs at precision/recall 1.0 — but
the metric's honest scope is the composed decision, not L2 in a vacuum. This is
appropriate for a decision layer measured by business outcome, stated here so the
attribution is not overclaimed.

## 6. Firewall re-verification (L3)
As with recovery grading, L3 re-verifies — it does not trust — that L2 produced
its ranking without reading the answer:
- static: L2 source references no manifest/ground-truth path;
- provenance: L2's inputs were the observation CSVs + card only (recompute the
  observation hash; confirm no manifest read).
A ranking that fails firewall re-verification is rejected, not graded.

## 7. Hand-offs (to other lanes)

- **L0 (design lane) — per-account latent value → unlocks Option B.** Emit, as
  an additive manifest field, each account's true latent value (or its
  components seg_value_mult + value_base + per-account engagement) so L3 can
  grade a *true-value* precision@K / NDCG that scores the within-category
  ordering. Additive only — existing L0 output stays byte-identical (same
  pattern as the no-wedge/TN hand-off). Until it lands, v1 grades Option A only.
- **L1 (card schema) — optional.** If future L2 versions weight by the card's
  per-segment cell_breakdown strength, no schema change is needed (already
  present); noted for completeness.

- **Harness (this lane) — per-seed L2 ranking.** Extend the harness to run L2 on
  each generated seed and emit its ranking with the quad, so L3 can compute
  precision@K across the multi-seed set (see §5.2). Required for Option-A
  multi-seed grading.

## 8. Status of this spec
v0.1 — design complete, gradable on Option A with the current manifest. Two
items are honestly open and flagged in-line: (1) segment-order is an observable
assumption (manifest cannot confirm it read-only); (2) within-category value
ordering is an Option-B measurement pending the L0 per-account-value hand-off.
These are surfaced as limitations, not hidden — consistent with the project's
"measure what you can verify; flag what you can't" discipline.
