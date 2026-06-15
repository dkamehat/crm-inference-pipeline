"""
Multi-seed quad generation (L1 / orchestration lane).

Per seed: run L0 emit into a private staging dir (full output incl. the manifest),
copy ONLY the two observation CSVs into a separate manifest-free input dir, run L1
recovery against that input dir, then assemble exactly the four grader files into
run_dir/seed_<n>/.

The manifest never enters L1's input dir, so the card stays manifest_read == false
and the grader's firewall re-verification passes. L0/L1 are imported and called,
never modified.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# make sibling layers importable when run directly
_FOUNDATION = Path(__file__).resolve().parent.parent
if str(_FOUNDATION) not in sys.path:
    sys.path.insert(0, str(_FOUNDATION))

import world_model.config as wmc
from world_model.simulate import WorldModel
from recovery import run as recovery_run

MANIFEST = "_ground_truth.json"          # L0 emit artifact name (grader: ground_truth.MANIFEST_NAME)
CARD = "recovery_card.json"
OBS_FILES = ("accounts.csv", "opportunities.csv")
_SEED_BASE = 1000


def default_seeds(n: int, base: int = _SEED_BASE) -> list[int]:
    """Fixed, reproducible schedule: base, base+1, ... (CLI-overridable)."""
    return [base + i for i in range(n)]


def generate_quad(seed: int, seed_dir, l1_seed: int | None = None) -> Path:
    """Generate one (manifest, card, accounts, opportunities) quad for `seed`.

    L1 sees only the observation CSVs (manifest excluded from its input)."""
    seed_dir = Path(seed_dir)
    seed_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as stage_s, tempfile.TemporaryDirectory() as obs_s:
        stage, obs = Path(stage_s), Path(obs_s)

        # 1. L0 emit (manifest + observations) into private staging
        WorldModel(wmc.Config(seed=seed), wmc.V1_PROFILE).simulate().emit(stage)

        # 2. observation-only input for L1 — manifest deliberately NOT copied here
        for f in OBS_FILES:
            shutil.copy(stage / f, obs / f)

        # 3. L1 recovery against the manifest-free observation dir
        rc = recovery_run.main(["--data-dir", str(obs),
                                "--out", str(seed_dir / CARD),
                                "--seed", str(seed if l1_seed is None else l1_seed)])
        if rc != 0:
            raise RuntimeError(f"L1 recovery failed for seed={seed} (rc={rc})")

        # 4. assemble EXACTLY the four grader files
        shutil.copy(stage / MANIFEST, seed_dir / MANIFEST)
        for f in OBS_FILES:
            shutil.copy(stage / f, seed_dir / f)

    return seed_dir


def generate_set(seeds: list[int], run_dir) -> list[Path]:
    """Generate the full quad set under run_dir/seed_<n>/ for each seed."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return [generate_quad(s, run_dir / f"seed_{s}") for s in seeds]
