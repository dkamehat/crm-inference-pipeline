# Harness — notes

## Firewall-preserving wiring (why two temp dirs)
L0 emit writes 8 files (incl. the manifest) into a private STAGING dir. L1 is then
run against a SEPARATE input dir holding only `accounts.csv` + `opportunities.csv`.
The manifest is never in L1's input, so L1's no-answer-read holds without trusting
it — the produced card keeps `manifest_read == false`. Only after L1 finishes are
exactly the four grader files assembled into `seed_<n>/`.

The grader's firewall re-verification still passes because the observation hash is
computed over the CSV *bytes* (path-sorted by basename), so it is identical whether
the CSVs live in the staging dir, L1's input dir, or the final seed dir.

## Additive / no modification
The harness imports `world_model` (L0) and `recovery.run` (L1) and calls their
public entry points. It does not modify L0/L1/L3 and does not touch their default
output paths (L1 is always run with an explicit `--data-dir` / `--out`).

## Reproducibility
Fixed schedule `default_seeds(n, base=1000)` = `[1000 .. 1000+n)`; CLI `--seeds`
overrides. `Config(seed=s)` makes `manifest.seed == s`. The L1 permutation seed is
set to the same `s` per seed, so the whole set regenerates byte-for-byte.

## Cost
Each seed runs a full L1 recovery (permutation null B=1000 ×2 + bootstrap + two
control axes), so generation is the slow step (~seconds per seed). N=50 is a few
minutes; reduce N for quick iterations. Generation is one-off — the grader then
reads the persisted set cheaply.

## V1 interpretation
V1's wedge is a profile constant (same category across seeds), so this set measures
recovery reliability of the canonical wedge across noise realizations + the
magnitude-bias distribution — not wedge-identity diversity (that needs more
profiles / B-L1-2).
