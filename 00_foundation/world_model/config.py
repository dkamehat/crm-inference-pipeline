"""
Configuration for the L0 WorldModel generator.

Two layers, deliberately separated so the core stays generic and additional
profiles are added rather than forked:

  - ``Config``        : structural, regime-independent knobs (scale, learning,
                        comp-driven distortion, capacity). Shared across profiles.
  - ``WorldProfile``  : profile-specific instantiation — segments, categories,
                        the planted wedge, territories, demand sources, loss mix.
                        ``V1_PROFILE`` is the thin-slice instance. Future regimes
                        register additional profiles in ``PROFILES``; the core
                        modules consume a profile and are never duplicated.

All values are abstract archetype settings: no real domain, employer, or figures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# Pipeline stages — generic Salesforce-shaped funnel, regime-independent.
STAGES: List[str] = [
    "01 - Prospecting",
    "02 - Qualification",
    "03 - Needs Analysis",
    "04 - Proposal",
    "05 - Negotiation",
    "06 - Closed Won",
    "07 - Closed Lost",
]
WON_STAGE = "06 - Closed Won"
LOST_STAGE = "07 - Closed Lost"
TERMINAL_STAGES = (WON_STAGE, LOST_STAGE)
# Highest stage an *open* opp can occupy (index of "05 - Negotiation").
MAX_OPEN_STAGE_IDX = STAGES.index("05 - Negotiation")


@dataclass
class Config:
    """Structural knobs shared by every profile (thin-slice defaults)."""

    seed: int = 42
    n_accounts: int = 1200
    t_periods: int = 18                  # PDCA cycles, in months
    start_year: int = 2024
    start_month: int = 1

    # ① hidden controlling-entity graph
    ctrl_share: float = 0.35             # fraction of accounts under a controlling entity
    ctrl_alpha: float = 1.3              # power-law exponent of control concentration
    hidden_parent_rate: float = 0.7      # fraction of links hidden/mis-parented in OBSERVED data
    ctrl_entity_cap: int = 45            # heavy-tail cap: no single entity owns more than this

    # ③ assumed-vs-true weights and PDCA learning
    prior_bias: float = 0.6              # magnitude of the org's initial miscalibration
    learn_rate: float = 0.18             # PDCA update speed toward the realized signal
    overfit_pull: float = 0.0            # vanity-signal chase — OFF in the thin slice

    # ④ comp-driven record-layer distortion
    sandbag_p: float = 0.18              # quarter-end: push a recorded win into next period
    happy_p: float = 0.12                # happy-ears: record an open opp one stage further
    stage_lag_p: float = 0.30            # fraction of open opps left at a stale stage
    stage_lag_cap_days: int = 540        # hard cap on days-open (auto-close guard; see simulate)
    close_optimism_days: int = 20        # recorded close pulled earlier than the true close

    # ⑤ capacity / two motions
    n_reps_smb: int = 8
    n_reps_named: int = 4
    rep_cap: int = 14                    # opps a rep can work per period

    # ⑥ exogenous
    launch_effect: bool = False          # product/launch bump — OFF in the thin slice


@dataclass
class WorldProfile:
    """Profile-specific instantiation of the six hidden structures."""

    name: str

    # account population
    segments: List[str]
    seg_volume: Dict[str, float]         # account mix by segment
    seg_base_logit: Dict[str, float]     # true convertibility, logit space
    seg_value_mult: Dict[str, float]     # account-value scale by segment
    value_base: float                    # base account value (abstract units)

    # categories + the planted wedge (high value, modest/low conversion)
    categories: List[str]
    wedge_segment: str
    wedge_category: str

    # territories and latent potential skew (⑤)
    territories: List[str]
    terr_potential: Dict[str, float]

    # demand sources (②) — logit-space lift avoids the probability ceiling
    sources: List[str]
    source_mix: List[float]
    source_logit: Dict[str, float]
    source_true_lift: Dict[str, float]   # legacy multiplicative view, kept for the manifest
    attrib_leak: float                   # fraction of partner WINS relabeled inbound (last-touch)

    # segment-conditional loss reasons (drives Pareto, not a flat uniform)
    loss_reasons: List[str]
    loss_profile: Dict[str, Dict[str, float]]

    # post-win activation profiles (the one genuinely good structure to preserve)
    usage_profiles: List[str]
    usage_profile_w: List[float]


# --------------------------------------------------------------------------- #
# V1 — high-frequency transactional platform (thin slice)
# --------------------------------------------------------------------------- #
V1_PROFILE = WorldProfile(
    name="v1",
    segments=["SMB", "MidMarket", "Enterprise"],
    seg_volume={"SMB": 0.62, "MidMarket": 0.30, "Enterprise": 0.08},
    seg_base_logit={"SMB": -1.2, "MidMarket": -0.7, "Enterprise": -0.2},
    seg_value_mult={"SMB": 0.4, "MidMarket": 1.0, "Enterprise": 2.6},
    value_base=8000.0,
    categories=[f"Cat-{c}" for c in "ABCDEFGH"],
    wedge_segment="MidMarket",
    wedge_category="Cat-D",
    territories=["T1", "T2", "T3", "T4", "T5"],
    terr_potential={"T1": 1.7, "T2": 1.5, "T3": 1.0, "T4": 0.6, "T5": 0.5},
    sources=["outbound", "inbound", "partner"],
    source_mix=[0.45, 0.35, 0.20],
    source_logit={"outbound": 0.0, "inbound": 0.15, "partner": 0.7},
    source_true_lift={"outbound": 1.0, "inbound": 1.1, "partner": 1.6},
    attrib_leak=0.45,
    loss_reasons=["Price", "Competitor", "No Decision", "Timing", "Product Fit"],
    loss_profile={
        "SMB":        {"Price": .45, "Competitor": .15, "No Decision": .12, "Timing": .15, "Product Fit": .13},
        "MidMarket":  {"Price": .25, "Competitor": .25, "No Decision": .20, "Timing": .15, "Product Fit": .15},
        "Enterprise": {"Price": .12, "Competitor": .18, "No Decision": .45, "Timing": .15, "Product Fit": .10},
    },
    usage_profiles=["growing", "stable", "declining", "spiky"],
    usage_profile_w=[0.40, 0.30, 0.20, 0.10],
)


# Registry — future regimes (V2 enterprise indirect-spend, V3 frontier) add an
# entry here with their own profile; the core engine is unchanged.
PROFILES: Dict[str, WorldProfile] = {
    "v1": V1_PROFILE,
}
