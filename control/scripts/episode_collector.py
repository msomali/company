#!/usr/bin/env python3
"""Episode collector (B4.4) — v2 §78 row 5 / §9 completeness.

Assembles and verifies the episode package for a task:
  episodes/TASK-###/
    task.yaml        (task-create)         — required
    state.yaml       (dispatcher)          — required
    log.jsonl        (dispatcher actions)  — required once any action occurred
    usage.yaml       (metering, Mode S)    — required once model calls occurred
    transcripts/     (session exports)     — recorded if present
    ESC-*.md         (escalations)         — recorded if present
    manifest.yaml    (WRITTEN BY THIS TOOL)

manifest.yaml carries: file inventory with sha256 content hashes, PR
references and CI links harvested from state history evidence and log
events, gate records referencing the task, §9 checklist results, and the
final status. --check mode verifies an existing manifest is current
(hash mismatch/missing/extra file → exit 1) without writing.

The collector only READS task state and WRITES manifest.yaml — it never
mutates task.yaml/state.yaml/log.jsonl (asserted in tests).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_RE = re.compile(r"(?:PR\s*#|pull/)(\d+)", re.IGNORECASE)
CI_RE = re.compile(r"https://github\.com/[^\s\"']+/actions/runs/\d+[^\s\"']*")


class CollectorError(Exception):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def harvest_references(task_dir: Path) -> dict:
    """PR numbers + CI links from state history evidence and log lines."""
    prs: set[int] = set()
    ci: set[str] = set()
    state = yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
    for entry in state.get("history", []):
        evidence = str(entry.get("evidence", ""))
        prs.update(int(m) for m in PR_RE.findall(evidence))
        ci.update(CI_RE.findall(evidence))
    log_path = task_dir / "log.jsonl"
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            blob = json.dumps(rec)
            prs.update(int(m) for m in PR_RE.findall(blob))
            ci.update(CI_RE.findall(blob))
    return {"pull_requests": sorted(prs), "ci_runs": sorted(ci)}


def gate_records_for(task_dir: Path, task_id: str) -> list[str]:
    gates_dir = task_dir.parents[1] / "gates"
    if not gates_dir.exists():
        return []
    return sorted(
        str(p.relative_to(task_dir.parents[1]))
        for p in gates_dir.glob(f"GATE-{task_id}-*.yaml")
    )


def completeness(task_dir: Path, state: dict) -> dict:
    """§9 checklist, honestly scored for what Phase 1 captures."""
    log_exists = (task_dir / "log.jsonl").exists()
    usage_exists = (task_dir / "usage.yaml").exists()
    transcripts = sorted(
        str(p.name) for p in (task_dir / "transcripts").glob("*")
    ) if (task_dir / "transcripts").exists() else []
    model_calls = 0
    if log_exists:
        model_calls = sum(
            1 for line in (task_dir / "log.jsonl").read_text().splitlines()
            if json.loads(line).get("event") == "model_usage"
        )
    # A task that has only been created (single INTAKE history entry) has
    # no dispatcher actions yet — log/usage/transcript checks are vacuous.
    acted = len(state.get("history", [])) > 1
    checks = {
        "task_envelope": (task_dir / "task.yaml").exists(),
        "state_transitions": bool(state.get("history")),
        "action_trace": log_exists or not acted,
        "cost_tokens": usage_exists or model_calls == 0,
        "transcripts": bool(transcripts) or model_calls == 0,
        "final_status_recorded": state.get("state") in ("CLOSED", "BLOCKED")
        or state.get("state") is not None,
    }
    return {"checks": checks, "transcripts": transcripts,
            "model_calls": model_calls,
            "complete": all(checks.values())}


def build_manifest(task_dir: Path) -> dict:
    for required in ("task.yaml", "state.yaml"):
        if not (task_dir / required).exists():
            raise CollectorError(f"{task_dir.name}: missing {required}")
    state = yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
    task_id = state["task_id"]
    files = {}
    for path in sorted(task_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.yaml":
            files[str(path.relative_to(task_dir))] = _sha256(path)
    return {
        "task_id": task_id,
        "collected_at": _now(),
        "final_state": state.get("state"),
        "rejection_cycles": state.get("rejection_cycles", 0),
        "iteration_count": state.get("iteration_count", 0),
        "files": files,
        "references": harvest_references(task_dir),
        "gate_records": gate_records_for(task_dir, task_id),
        "completeness": completeness(task_dir, state),
    }


def collect(task_dir: Path, check: bool = False) -> tuple[dict, list[str]]:
    manifest = build_manifest(task_dir)
    manifest_path = task_dir / "manifest.yaml"
    problems: list[str] = []
    if check:
        if not manifest_path.exists():
            problems.append("manifest.yaml missing — run the collector")
        else:
            old = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            for rel, digest in manifest["files"].items():
                prev = old.get("files", {}).get(rel)
                if prev is None:
                    problems.append(f"new file since collection: {rel}")
                elif prev != digest:
                    problems.append(f"content changed since collection: {rel}")
            for rel in old.get("files", {}):
                if rel not in manifest["files"]:
                    problems.append(f"file vanished since collection: {rel}")
            # ADR-B007 bound requirement: the manifest attests to gate
            # records, and --check resolves them through THIS tree (the lane
            # worktree once PR 2 wires the caller). A record the manifest
            # names but that is absent from this tree fails --check — a
            # record present only in another tree (the host clone) does not
            # rescue a lane that lacks it. This is the #122 gap made
            # detectable: a manifest must never attest to records on no lane
            # ref. (build_manifest's gate glob is already tree-local, so
            # freshly collected manifests list only what is present here;
            # this guards a manifest carried forward against a tree that
            # since lost a record.)
            project_dir = task_dir.parents[1]
            for rel in old.get("gate_records", []):
                if not (project_dir / rel).is_file():
                    problems.append(
                        f"gate record vanished from the lane: {rel}")
        return manifest, problems
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return manifest, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_dir", type=Path,
                        help="projects/PROJECT-###/episodes/TASK-###")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest, problems = collect(args.task_dir, check=args.check)
    except CollectorError as exc:
        print(f"collector: FAIL {exc}")
        return 1
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        return 1
    verdict = "complete" if manifest["completeness"]["complete"] else "INCOMPLETE"
    print(f"episode {manifest['task_id']}: {len(manifest['files'])} file(s), "
          f"{verdict}, refs: PRs {manifest['references']['pull_requests']}")
    return 0 if manifest["completeness"]["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
