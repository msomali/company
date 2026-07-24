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
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_RE = re.compile(r"(?:PR\s*#|pull/)(\d+)", re.IGNORECASE)
CI_RE = re.compile(r"https://github\.com/[^\s\"']+/actions/runs/\d+[^\s\"']*")


class CollectorError(Exception):
    pass


def _default_git_rc(argv: list[str]) -> int:
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=60).returncode


def git_tree_root(start: Path) -> Path | None:
    """The git tree root at/above ``start`` (``.git`` is a dir in the clone,
    a FILE in a lane worktree — ``exists()`` catches both)."""
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def make_ref_tracker(tree_root: Path, runner=None):
    """ADR-B007 (owner addition, 2026-07-23): 'tracked on a ref' means the
    path exists in HEAD's tree — committed to the lane branch — not merely
    present on disk. Presence-on-disk-only is exactly what #122 violated.
    Returns ``is_tracked(repo_rel) -> bool`` via ``git cat-file -e HEAD:<rel>``
    (repo_rel is relative to ``tree_root``). Injectable runner keeps tests
    offline."""
    run = runner or _default_git_rc

    def is_tracked(repo_rel: str) -> bool:
        return run(["git", "-C", str(tree_root), "cat-file", "-e",
                    f"HEAD:{repo_rel}"]) == 0

    return is_tracked


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


def gate_records_for(task_dir: Path, task_id: str, is_tracked=None) -> list[str]:
    """Gate records for ``task_id`` in this tree, relative to the project dir.
    When ``is_tracked`` is given (lane context), a record present on disk but
    on NO ref is EXCLUDED — the manifest never attests to records that exist
    on no lane ref (ADR-B007 closing line; the #122 defect)."""
    project_dir = task_dir.parents[1]
    gates_dir = project_dir / "gates"
    if not gates_dir.exists():
        return []
    tree_root = task_dir.parents[3]
    out: list[str] = []
    for p in sorted(gates_dir.glob(f"GATE-{task_id}-*.yaml")):
        if is_tracked is not None and not is_tracked(
                str(p.relative_to(tree_root))):
            continue
        out.append(str(p.relative_to(project_dir)))
    return out


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


def build_manifest(task_dir: Path, is_tracked=None) -> dict:
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
        "gate_records": gate_records_for(task_dir, task_id, is_tracked),
        "completeness": completeness(task_dir, state),
    }


def collect(task_dir: Path, check: bool = False, verify_refs: bool = False,
            git_runner=None) -> tuple[dict, list[str]]:
    """Build (or --check) the episode manifest. ``verify_refs`` (ADR-B007,
    owner addition) resolves the tree root and requires attested gate records
    to be TRACKED ON A REF (committed), not merely present on disk — the
    dispatcher and the close-runbook CLI run against the lane worktree with
    this on. Left False, the collector is filesystem-only (library/test
    default)."""
    is_tracked = None
    if verify_refs:
        tree_root = git_tree_root(task_dir)
        if tree_root is None:
            raise CollectorError(
                f"{task_dir}: not inside a git tree — cannot verify gate"
                " records are on a ref; run against the lane worktree or pass"
                " --no-verify-refs"
            )
        is_tracked = make_ref_tracker(tree_root, runner=git_runner)
    manifest = build_manifest(task_dir, is_tracked=is_tracked)
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
            tree_root = task_dir.parents[3]
            for rel in old.get("gate_records", []):
                p = project_dir / rel
                if not p.is_file():
                    problems.append(
                        f"gate record vanished from the lane: {rel}")
                elif is_tracked is not None and not is_tracked(
                        str(p.relative_to(tree_root))):
                    problems.append(
                        f"gate record present but on NO lane ref "
                        f"(untracked — the #122 defect): {rel}")
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
    # ADR-B007: the close-runbook collector runs against the lane worktree,
    # where gate records MUST be on a ref (default on). --no-verify-refs is
    # the escape for a non-git tree (e.g. an already-merged main checkout).
    parser.add_argument("--verify-refs", dest="verify_refs",
                        action="store_true", default=True)
    parser.add_argument("--no-verify-refs", dest="verify_refs",
                        action="store_false")
    args = parser.parse_args(argv)
    try:
        manifest, problems = collect(args.task_dir, check=args.check,
                                     verify_refs=args.verify_refs)
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
