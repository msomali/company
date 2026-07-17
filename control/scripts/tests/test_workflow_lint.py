"""Tests for workflow_lint.py — including the exact 2026-07-17 incident
signature: a workflow whose secrets expression was clobbered by a `***`
redaction artifact must fail lint."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import workflow_lint as wl  # noqa: E402

VALID = """\
name: demo
on: [pull_request]
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""


def test_all_repo_workflows_clean():
    assert wl.main() == 0


def test_valid_workflow_passes():
    assert wl.lint_text(VALID) == []


def test_incident_signature_fails():
    """The gate-writer breakage, verbatim shape: env value replaced by ***."""
    broken = VALID.replace(
        "steps:",
        "env:\n      GH_TOKEN: " + "*" * 3 + " secrets.X }}\n    steps:",
    )
    problems = wl.lint_text(broken)
    assert any("redaction artifact" in p for p in problems)


def test_unparseable_yaml_fails():
    problems = wl.lint_text("name: demo\non: [pull_request\njobs: {")
    assert any("yaml parse error" in p for p in problems)


def test_missing_jobs_fails():
    problems = wl.lint_text("name: demo\non: [push]\n")
    assert any("missing top-level key: jobs" in p for p in problems)


def test_bare_on_boolean_quirk_accepted():
    assert wl.lint_text(VALID.replace("on: [pull_request]", "on:\n  push:")) == []


def test_job_without_steps_fails():
    broken = "name: d\non: [push]\njobs:\n  x:\n    runs-on: ubuntu-latest\n"
    problems = wl.lint_text(broken)
    assert any("neither steps nor uses" in p for p in problems)


def test_broken_workflow_file_fails_main(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("jobs: [")
    assert wl.main([str(bad)]) == 1
