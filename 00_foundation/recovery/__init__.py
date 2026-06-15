"""
L1 Recovery layer — infer the hidden value-concentration wedge (signal 06) from
the OBSERVED projection alone.

Firewall (L1-RECOVERY-SPEC §2, §6 INV-FW/INV-ATT): this package reads ONLY the
observed CSVs (accounts, opportunities). It never imports or opens the L0
generator internals or the ground-truth manifest — recovery must infer the hidden
structure, not look up the answer key. Scoring of whether the inference is correct
is L3's job, not L1's.

Modules:
  io       — observed input contract + observation hash (spec §3)
  wedge    — two-way effect decomposition + empirical-Bayes pooling, existence
             gate, membership (spec §5)
  guards   — permutation-null calibration, quantile membership, bootstrap
             stability (spec §7)
  baseline — L0 self_check rule ported for parity comparison (spec §5.5)
  card     — recovery card assembly (spec §12 schema)
  run      — observation -> card entry point
"""

from .io import load_won, observation_hash, check_preconditions, WON_STAGE
from .wedge import recover, RecoveryResult
from .baseline import baseline_flags
from .card import build_card

__all__ = [
    "load_won",
    "observation_hash",
    "check_preconditions",
    "WON_STAGE",
    "recover",
    "RecoveryResult",
    "baseline_flags",
    "build_card",
]
