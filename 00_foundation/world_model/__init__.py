"""
L0 WorldModel — a hidden causal generator for Salesforce-shaped synthetic data.

The observed CRM tables are a *lossy projection* of a hidden world. This package
defines that hidden world (true conversion weights, ownership graph, demand
sources, comp-driven distortion) and emits both the observed CSVs and a
ground-truth manifest — the answer key against which later layers check whether
analysis *recovers* the planted structure rather than narrating the surface.

Layering:
  config   — Config (structural knobs) + WorldProfile (profile-specific values)
  graph    — ControllingEntityGraph  (hidden ownership, power-law concentration)
  models   — TrueConversionModel / AssumedScoreModel  (outcome vs. priority)
  reps     — RepBehaviorModel  (comp-driven record-layer distortion)
  market   — Market  (seasonality, demand sources, territory latent potential)
  simulate — WorldModel  (the period loop that ties the above together)
  emit     — observed CSV + ground-truth manifest
  self_check — planted-signal recovery report (human-readable + machine-checkable)

All naming is generic by design: this models a high-frequency transactional
platform archetype, with no real domain, employer, or figures anywhere.
"""

from .config import Config, WorldProfile, PROFILES, V1_PROFILE, STAGES
from .simulate import WorldModel
from .self_check import run_checks, self_check

__all__ = [
    "Config",
    "WorldProfile",
    "PROFILES",
    "V1_PROFILE",
    "STAGES",
    "WorldModel",
    "run_checks",
    "self_check",
]
