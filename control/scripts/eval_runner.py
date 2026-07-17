#!/usr/bin/env python3
"""eval-runner (POL-006, B5.1) — deterministic golden-task evaluation, v2.1 §84.

Phase-1 scope: deterministic checks only. Judge-based scoring slots stay
disabled until Phase 2 (§84.5). Blocking semantics per §57: any mandatory
check failure fails the run; averages never offset a failed mandatory check.

Case format (control/evals/<agent>/case-*.yaml):
  case_id:        e.g. SDE-GT-001 (unique)
  description:    one line
  input_envelope: task envelope, validated against control/schemas/task.json
  fixture:        dir relative to the case file — the workspace under
                  evaluation (golden solution during bootstrap; agent output
                  once agents are live)
  expect:         pass (default) | fail — `fail` marks a *seeded failure*
                  case: it MUST fail its checks (proves the harness blocks);
                  if it passes, the run fails.
  checks:         list of {kind: ...} — see CHECK_KINDS

Check kinds (all deterministic):
  file_exists              {path}    — path exists inside the fixture
  command_passes           {cmd}     — cmd exits 0, cwd=fixture; `{repo}`
                                       expands to the repo root, `{python}`
                                       to the running interpreter
  frontmatter_valid        {glob}    — every fixture file matching glob that
                                       opens with a `---` fence parses as YAML
  forbidden_pattern_absent {pattern} — regex matches nothing in the fixture
  budget_respected         {field}   — envelope budgets[field] is a positive int

Exit code 0 = all cases behave as expected; 1 = any deviation (this is the
blocking signal §84.3 requires). Failure sources feed new cases per §84.4.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_SCHEMA = REPO_ROOT / "control" / "schemas" / "task.json"
CHECK_KINDS = frozenset(
    {
        "file_exists",
        "command_passes",
        "frontmatter_valid",
        "forbidden_pattern_absent",
        "budget_respected",
    }
)
COMMAND_TIMEOUT_S = 300
FENCE = "---"


def _fixture_files(fixture: Path):
    return (p for p in sorted(fixture.rglob("*")) if p.is_file())


def run_check(check: dict, fixture: Path | None, envelope: dict) -> str | None:
    """Return None on pass, else a failure message."""
    kind = check.get("kind")
    if kind not in CHECK_KINDS:
        return f"unknown check kind: {kind!r}"

    if kind == "budget_respected":
        field = check.get("field", "")
        value = (envelope.get("budgets") or {}).get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return None
        return f"budgets.{field} missing or not a positive integer: {value!r}"

    if fixture is None:
        return f"{kind}: case has no fixture directory"

    if kind == "file_exists":
        path = check.get("path", "")
        return None if (fixture / path).is_file() else f"missing file: {path}"

    if kind == "command_passes":
        cmd = (
            check.get("cmd", "")
            .replace("{repo}", str(REPO_ROOT))
            .replace("{python}", sys.executable)
        )
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=fixture,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return f"command timed out ({COMMAND_TIMEOUT_S}s): {cmd}"
        if proc.returncode == 0:
            return None
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        return f"command failed rc={proc.returncode}: {cmd} :: " + " | ".join(tail)

    if kind == "frontmatter_valid":
        pattern = check.get("glob", "**/*.md")
        bad = []
        for path in sorted(fixture.glob(pattern)):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.startswith(FENCE):
                continue
            try:
                _, fence, rest = text.split(FENCE, 2)
            except ValueError:
                bad.append(f"{path.relative_to(fixture)}: unterminated fence")
                continue
            try:
                parsed = yaml.safe_load(fence)
            except yaml.YAMLError as exc:
                bad.append(f"{path.relative_to(fixture)}: {exc}")
                continue
            if not isinstance(parsed, dict) or not parsed:
                bad.append(f"{path.relative_to(fixture)}: empty front matter")
        return "; ".join(bad) if bad else None

    # forbidden_pattern_absent
    try:
        regex = re.compile(check.get("pattern", ""))
    except re.error as exc:
        return f"invalid forbidden pattern: {exc}"
    hits = []
    for path in _fixture_files(fixture):
        text = path.read_text(encoding="utf-8", errors="replace")
        if regex.search(text):
            hits.append(str(path.relative_to(fixture)))
    return f"forbidden pattern found in: {', '.join(hits)}" if hits else None


def evaluate_case(case_path: Path, validator: Draft7Validator) -> dict:
    try:
        shown = str(case_path.relative_to(REPO_ROOT))
    except ValueError:  # case outside the repo (e.g. test harness tmp dir)
        shown = str(case_path)
    result = {"case": shown, "failures": []}
    try:
        case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        result["failures"].append(f"unparseable case: {exc}")
        return result
    if not isinstance(case, dict):
        result["failures"].append("case is not a mapping")
        return result

    result["case_id"] = case.get("case_id", "?")
    result["expect"] = case.get("expect", "pass")
    if result["expect"] not in ("pass", "fail"):
        result["failures"].append(f"invalid expect: {result['expect']!r}")
        return result

    for field in ("case_id", "description", "input_envelope", "checks"):
        if field not in case:
            result["failures"].append(f"case missing field: {field}")
    if result["failures"]:
        return result

    envelope = case["input_envelope"]
    schema_errors = sorted(validator.iter_errors(envelope), key=str)
    for err in schema_errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        result["failures"].append(f"envelope invalid at {loc}: {err.message}")

    fixture = None
    if "fixture" in case:
        fixture = (case_path.parent / case["fixture"]).resolve()
        if not fixture.is_dir():
            result["failures"].append(f"fixture dir not found: {case['fixture']}")
            fixture = None

    checks = case["checks"]
    if not isinstance(checks, list) or not checks:
        result["failures"].append("checks must be a non-empty list")
        return result
    for check in checks:
        msg = run_check(check, fixture, envelope)
        if msg:
            result["failures"].append(msg)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic eval runner (§84)")
    ap.add_argument("--config", default="control/evals/runner.yaml")
    ap.add_argument("--case", action="append", help="run specific case file(s)")
    ap.add_argument("--report", help="write JSON report to this path")
    args = ap.parse_args(argv)

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.case:
        case_paths = [Path(c).resolve() for c in args.case]
    else:
        case_paths = sorted(REPO_ROOT.glob(config["case_glob"]))
    if not case_paths:
        print("eval-runner: no cases found", file=sys.stderr)
        return 1

    validator = Draft7Validator(json.loads(TASK_SCHEMA.read_text(encoding="utf-8")))
    results, blocking = [], []
    seen_ids: set[str] = set()
    for case_path in case_paths:
        res = evaluate_case(case_path, validator)
        cid = res.get("case_id", "?")
        if cid in seen_ids:
            res["failures"].append(f"duplicate case_id: {cid}")
        seen_ids.add(cid)
        failed = bool(res["failures"])
        expect = res.get("expect", "pass")
        if expect == "fail" and not failed:
            res["verdict"] = "UNEXPECTED-PASS (seeded failure passed — harness broken)"
            blocking.append(res)
        elif expect == "fail":
            res["verdict"] = "BLOCKED-AS-SEEDED"
        elif failed:
            res["verdict"] = "FAIL"
            blocking.append(res)
        else:
            res["verdict"] = "PASS"
        results.append(res)
        print(f"{res['verdict']:<12} {cid:<14} {res['case']}")
        for msg in res["failures"]:
            print(f"    - {msg}")

    summary = {
        "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cases": results,
        "blocking_failures": len(blocking),
    }
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if blocking:
        print(f"eval-runner: BLOCKED — {len(blocking)} mandatory failure(s) (§57)")
        return 1
    print(f"eval-runner: {len(results)} case(s) behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
