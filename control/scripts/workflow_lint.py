#!/usr/bin/env python3
"""workflow-lint (B5.2 fix-forward 2, 2026-07-17) — no syntactically invalid
GitHub workflow may merge green again.

Incident: an editor-side redaction artifact replaced a `$ {{ ... }}` secrets
expression with `***` in .github/workflows/gate-writer.yml; the file merged
green (nothing parsed workflows in CI), GitHub marked the workflow invalid,
a merge event was consumed with no run, and workflow_dispatch went dark.

Checks per .github/workflows/*.yml|yaml (deterministic, stdlib + pyyaml):
  1. file parses via yaml.safe_load
  2. top-level mapping carries name / on / jobs (YAML 1.1 quirk: bare `on:`
     loads as boolean True — accepted)
  3. jobs is a non-empty mapping; every job has steps (or `uses` for reusable
     workflow calls)
  4. no `***` redaction artifact anywhere in the file — the exact incident
     signature

Exit 0 = clean; 1 = violations (printed as `path: message`).
actionlint (deeper semantic lint) is a candidate upgrade; deliberately not
vendored here to keep CI supply-chain surface unchanged — needs an owner
decision (see PR).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
REDACTION_ARTIFACT = "*" * 3


def lint_text(text: str) -> list[str]:
    """Lint one workflow file's content; return problems."""
    problems: list[str] = []
    if REDACTION_ARTIFACT in text:
        problems.append(
            "redaction artifact '***' present (incident signature 2026-07-17)"
        )
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        problems.append(f"yaml parse error: {exc}")
        return problems
    if not isinstance(doc, dict):
        problems.append("not a YAML mapping at top level")
        return problems
    keys = {"on" if k is True else k for k in doc}
    for required in ("name", "on", "jobs"):
        if required not in keys:
            problems.append(f"missing top-level key: {required}")
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        problems.append("jobs must be a non-empty mapping")
        return problems
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            problems.append(f"job {job_id!r}: not a mapping")
        elif "steps" not in job and "uses" not in job:
            problems.append(f"job {job_id!r}: has neither steps nor uses")
    return problems


def main(argv: list[str] | None = None) -> int:
    paths = (
        [Path(p) for p in argv]
        if argv
        else sorted(
            p
            for pattern in ("*.yml", "*.yaml")
            for p in WORKFLOWS_DIR.glob(pattern)
        )
    )
    if not paths:
        print("workflow-lint: no workflow files found", file=sys.stderr)
        return 1
    failures = 0
    for path in paths:
        for problem in lint_text(path.read_text(encoding="utf-8")):
            print(f"{path}: {problem}")
            failures += 1
    if failures:
        print(f"workflow-lint: {failures} problem(s)")
        return 1
    print(f"workflow-lint: clean ({len(paths)} workflow(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
