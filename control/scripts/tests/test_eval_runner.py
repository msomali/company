"""Tests for eval_runner.py (B5.1) — including the seeded-failure blocking
proof required by BA-6 ("CI blocks a seeded failing case"): these tests run
in the required `lint` check on every PR, so a harness that stops blocking
turns the required check red."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parents[1]
import eval_runner  # noqa: E402

CONFIG = str(REPO / "control" / "evals" / "runner.yaml")
SDE_CASE = REPO / "control" / "evals" / "sde" / "case-001.yaml"
SEEDED = REPO / "control" / "evals" / "sde" / "case-002-seeded-failure.yaml"


def run(args):
    return eval_runner.main(args)


def test_full_suite_behaves_as_expected():
    assert run(["--config", CONFIG]) == 0


def test_golden_sde_case_passes():
    assert run(["--config", CONFIG, "--case", str(SDE_CASE)]) == 0


def test_seeded_failure_blocks_when_not_expected(tmp_path):
    """THE blocking proof: the seeded case, stripped of `expect: fail`,
    must make the runner exit nonzero."""
    case = yaml.safe_load(SEEDED.read_text())
    case.pop("expect")
    case["case_id"] = "SDE-GT-002-UNSEEDED"
    case["fixture"] = str(SEEDED.parent / case["fixture"])
    hot = tmp_path / "case-002-hot.yaml"
    hot.write_text(yaml.safe_dump(case))
    assert run(["--config", CONFIG, "--case", str(hot)]) == 1


def test_seeded_failure_case_is_expected_in_suite():
    assert run(["--config", CONFIG, "--case", str(SEEDED)]) == 0


def test_unexpected_pass_of_seeded_case_blocks(tmp_path):
    """A seeded case that passes means the harness is broken — must block."""
    case = yaml.safe_load(SDE_CASE.read_text())  # passing case...
    case["expect"] = "fail"                      # ...claimed as seeded failure
    case["case_id"] = "SDE-GT-001-MISSEEDED"
    case["fixture"] = str(SDE_CASE.parent / case["fixture"])
    hot = tmp_path / "case-001-hot.yaml"
    hot.write_text(yaml.safe_dump(case))
    assert run(["--config", CONFIG, "--case", str(hot)]) == 1


def test_invalid_envelope_blocks(tmp_path):
    case = yaml.safe_load(SDE_CASE.read_text())
    case["case_id"] = "SDE-GT-BAD-ENV"
    case["fixture"] = str(SDE_CASE.parent / case["fixture"])
    del case["input_envelope"]["acceptance_criteria"]   # schema-required
    hot = tmp_path / "case-bad-env.yaml"
    hot.write_text(yaml.safe_dump(case))
    assert run(["--config", CONFIG, "--case", str(hot)]) == 1


def test_report_written(tmp_path):
    report = tmp_path / "out" / "report.json"
    assert run(["--config", CONFIG, "--report", str(report)]) == 0
    assert report.is_file() and b'"blocking_failures": 0' in report.read_bytes()


def test_forbidden_pattern_check(tmp_path):
    fixture = tmp_path / "fx"
    fixture.mkdir()
    (fixture / "leak.txt").write_text("canary-token present")
    msg = eval_runner.run_check(
        {"kind": "forbidden_pattern_absent", "pattern": r"canary-token"},
        fixture,
        {},
    )
    assert msg and "leak.txt" in msg


def test_budget_check_rejects_zero():
    msg = eval_runner.run_check(
        {"kind": "budget_respected", "field": "tool_call_limit"},
        None,
        {"budgets": {"tool_call_limit": 0}},
    )
    assert msg is not None
