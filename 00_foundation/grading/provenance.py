"""
Pure observation-hash primitive (L3-GRADING-SPEC §4.4).

Replicates the provenance hash DEFINED by the card schema (L1-RECOVERY-SPEC §2.3):
sha256 over the raw bytes of the two observed CSVs, path-sorted for stability. This
is a standalone primitive — it does NOT import L1 recovery logic — so L3 can audit
the firewall attestation from the answer side without executing the recovery.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def observation_hash(accounts_path, opps_path) -> str:
    h = hashlib.sha256()
    for p in sorted([str(accounts_path), str(opps_path)]):
        h.update(Path(p).read_bytes())
    return h.hexdigest()
