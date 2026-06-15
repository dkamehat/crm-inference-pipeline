"""
Orchestration harness (L1 / orchestration lane).

Produces the multi-seed set of (manifest, card, accounts, opportunities) quads that
the L3 grader consumes. For each seed it runs L0 (the generator) and L1 (the
recovery) and persists exactly the four files the grader expects into
run_dir/seed_<n>/.

Firewall discipline (the point of this lane): L1 receives ONLY the two observation
CSVs — the manifest is never passed to L1 and never placed in L1's input directory,
so every generated card keeps manifest_read == false. The harness only IMPORTS and
CALLS L0/L1/L3; it modifies none of them (additive).

Generated quads are artifacts (git-ignored run-dir); only harness source + tests
are committed.
"""

from .generate import default_seeds, generate_quad, generate_set, MANIFEST, CARD, OBS_FILES

__all__ = [
    "default_seeds", "generate_quad", "generate_set",
    "MANIFEST", "CARD", "OBS_FILES",
]
