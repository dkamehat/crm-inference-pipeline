"""
Pytest for the orchestration harness (firewall-preserving wiring + small-N e2e).

Naming: test_<subject>_<property>; docstrings state the invariant. Runs L0+L1 for a
couple of seeds, so it is the heavier suite in the repo (still seconds).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from harness import generate
from grading.grade import Case, grade_cases


def test_seed_schedule_is_fixed_and_reproducible():
    """INV: the seed schedule is fixed/deterministic."""
    assert generate.default_seeds(3) == [1000, 1001, 1002]
    assert generate.default_seeds(2, base=42) == [42, 43]


def test_l1_input_never_contains_the_manifest(tmp_path, monkeypatch):
    """INV (firewall): the harness passes L1 only the observation CSVs — the manifest
    is never in L1's input dir. Spy on the data-dir handed to L1 at call time."""
    seen = {}
    real_main = generate.recovery_run.main

    def spy(argv):
        data_dir = argv[argv.index("--data-dir") + 1]
        seen["files"] = sorted(os.listdir(data_dir))
        return real_main(argv)

    monkeypatch.setattr(generate.recovery_run, "main", spy)
    generate.generate_quad(1000, tmp_path / "seed_1000")

    assert set(generate.OBS_FILES).issubset(seen["files"])
    assert generate.MANIFEST not in seen["files"]                 # manifest absent from L1 input
    assert all(not f.endswith(".json") for f in seen["files"])    # no manifest/card json reachable


def test_seed_dir_has_exactly_the_four_grader_files(tmp_path):
    """INV: seed_<n>/ contains exactly the four files the grader expects."""
    d = generate.generate_quad(1000, tmp_path / "seed_1000")
    assert sorted(os.listdir(d)) == sorted(
        [generate.MANIFEST, generate.CARD, *generate.OBS_FILES])


def test_generated_card_is_manifest_read_false(tmp_path):
    """INV (firewall): the produced card keeps manifest_read == false."""
    d = generate.generate_quad(1000, tmp_path / "seed_1000")
    card = json.loads((d / generate.CARD).read_text())
    assert card["provenance"]["manifest_read"] is False


def test_manifest_seed_matches_schedule(tmp_path):
    """INV: manifest.seed equals the schedule seed (reproducibility binding)."""
    d = generate.generate_quad(1234, tmp_path / "seed_1234")
    manifest = json.loads((d / generate.MANIFEST).read_text())
    assert manifest["seed"] == 1234


def test_end_to_end_small_set_grades_clean(tmp_path):
    """e2e smoke: a small generated set is gradable, firewall passes, counts reconcile."""
    seeds = generate.default_seeds(2)
    run_dir = tmp_path / "run"
    generate.generate_set(seeds, run_dir)
    cases = []
    for s in seeds:
        d = run_dir / f"seed_{s}"
        cases.append(Case(str(d / generate.MANIFEST), str(d / generate.CARD),
                          str(d / "accounts.csv"), str(d / "opportunities.csv"),
                          label=f"seed_{s}"))
    rep = grade_cases(cases)
    assert rep["n_cases"] == 2
    assert rep["rejected"] == 0                       # firewall re-verify passes
    assert rep["reconciliation_ok"] is True
    assert (rep["confusion"]["TP"] + rep["confusion"]["FP"]
            + rep["confusion"]["FN"]) == 2
