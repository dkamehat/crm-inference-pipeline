# Harness — notes

## Firewall-preserving wiring (why two temp dirs)
L0 emit writes 8 files (incl. the manifest) into a private STAGING dir. L1 (recovery)
and then L2 (decision) are run against a SEPARATE input dir holding only
`accounts.csv` + `opportunities.csv` (L2 also reads L1's card, which carries no
answer). The manifest is never in their input, so the no-answer-read holds without
trusting it — both the card and the ranking keep `manifest_read == false`. Only after
L1/L2 finish are the grader files (the quad + `decision_ranking.json`) assembled into
`seed_<n>/`.

The graders' firewall re-verification still passes because the observation hash is
computed over the CSV *bytes* (path-sorted by basename), so it is identical whether
the CSVs live in the staging dir, the L1/L2 input dir, or the final seed dir.

## Additive / no modification
The harness imports `world_model` (L0), `recovery.run` (L1), and `decision.run` (L2)
and calls their public entry points. It does not modify L0/L1/L2/L3 and does not touch
their default output paths (L1/L2 are always run with explicit `--data-dir` / `--out`).

## Reproducibility
Fixed schedule `default_seeds(n, base=1000)` = `[1000 .. 1000+n)`; CLI `--seeds`
overrides. `Config(seed=s)` makes `manifest.seed == s`. The L1 permutation seed is
set to the same `s` per seed, so the whole set regenerates byte-for-byte.

## Cost
Each seed runs a full L1 recovery (permutation null B=1000 ×2 + bootstrap + two
control axes) plus a cheap L2 ranking, so L1 is the slow step (~seconds per seed).
N=50 is a few minutes; reduce N for quick iterations. Generation is one-off — the
graders then read the persisted set cheaply.

## V1 interpretation
V1's wedge is a profile constant (same category across seeds), so this set measures
recovery reliability of the canonical wedge across noise realizations + the
magnitude-bias distribution — not wedge-identity diversity (that needs more
profiles / B-L1-2).
