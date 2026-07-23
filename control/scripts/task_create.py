#!/usr/bin/env python3
"""task-create (B4.1) — v2 §82.1 acceptance specification.

Validates a task envelope against control/schemas/task.json; allocates the
next TASK-### within the project's episodes/ directory; writes
  projects/<PROJECT>/episodes/TASK-###/task.yaml
  projects/<PROJECT>/episodes/TASK-###/state.yaml   (state: INTAKE)
and prints the allocated ID.

Rejection contract (§82.1): invalid input → exit 2 with every failing field
listed; NOTHING is written; no model call occurs (this tool contains no model
client by construction).

Usage:
  task_create.py path/to/envelope.yaml            # create
  task_create.py --validate-only path/to/envelope.yaml    # pre-creation
  task_create.py --validate-record path/to/task.yaml      # post-creation

The two validate modes differ by ONE structural rule: --validate-only is the
intake contract (task_id must be ABSENT — task-create allocates it, §82.1),
so it structurally rejects every legitimate task.yaml the moment creation
has happened. --validate-record (owner finding, 2026-07-23) judges a
post-creation record as it exists on disk — task_id REQUIRED, the same
schema + semantic checks otherwise, plus layout consistency when the file
sits inside an episodes/TASK-### directory. Neither mode writes anything.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_SCHEMA = REPO_ROOT / "control" / "schemas" / "task.json"
STATE_SCHEMA = REPO_ROOT / "control" / "schemas" / "state.json"
PROJECTS_DIR = REPO_ROOT / "projects"

EXIT_OK = 0
EXIT_REJECTED = 2


class Rejection(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def load_envelope(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Rejection([f"envelope: unreadable or invalid YAML ({exc})"])
    if not isinstance(data, dict):
        raise Rejection(["envelope: must be a YAML mapping"])
    return data


def allocate_task_id(episodes_dir: Path) -> str:
    """Next-integer allocation within the project (v1 §52.5); TASK-### ids are
    idempotency keys (v2 §78 row 7)."""
    highest = 0
    if episodes_dir.exists():
        for entry in episodes_dir.iterdir():
            name = entry.name
            if entry.is_dir() and name.startswith("TASK-"):
                suffix = name[5:]
                if suffix.isdigit():
                    highest = max(highest, int(suffix))
    return f"TASK-{highest + 1:03d}"


def validate(envelope: dict) -> list[str]:
    """Return every failing field (never just the first)."""
    validator = Draft7Validator(json.loads(TASK_SCHEMA.read_text()))
    problems = []
    for err in sorted(validator.iter_errors(envelope), key=str):
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        problems.append(f"{where}: {err.message}")

    # Semantic checks beyond the schema (§82.1 "no model call occurs" is
    # structural: this module imports no model client).
    if envelope.get("risk_class") == "prohibited":
        problems.append(
            "risk_class: 'prohibited' work is rejected at intake by definition "
            "(v1 severity model); it cannot be dispatched"
        )
    project_id = envelope.get("project_id")
    if isinstance(project_id, str) and project_id:
        if not (PROJECTS_DIR / project_id).is_dir():
            problems.append(
                f"project_id: no such project directory projects/{project_id}/ "
                "(charter must exist before tasks are created)"
            )
    requested_by = envelope.get("requested_by")
    assigned_role = envelope.get("assigned_role")
    if requested_by and assigned_role and requested_by == assigned_role:
        problems.append(
            "requested_by/assigned_role: requester and assignee are the same "
            "identity — separation of duties (v1 §8) requires distinct roles"
        )
    return problems


def validate_record(record_path: Path) -> str:
    """Validate a POST-creation record (task.yaml with its allocated id).

    Motivation (owner finding, 2026-07-23): live envelope amendments — the
    TASK-003 iteration-2 rescope — needed re-validation, but --validate-only
    structurally rejects any record with task_id present. Same authority as
    create(): every failing field listed, exit 2, nothing written, no model
    call (structural — no model client in this module).
    """
    record = load_envelope(record_path)
    if "task_id" not in record:
        raise Rejection([
            "task_id: missing — a post-creation record carries its allocated "
            "id (validating a pre-creation envelope? use --validate-only)"
        ])
    problems = validate(record)

    # Layout consistency — judged only when the record actually sits in an
    # episodes/TASK-### directory (amendment drafts in /tmp validate fine).
    parent = record_path.resolve().parent
    tid = record.get("task_id")
    if re.fullmatch(r"TASK-[0-9]{3,}", parent.name):
        if isinstance(tid, str) and tid != parent.name:
            problems.append(
                f"task_id: {tid} does not match its episode directory "
                f"{parent.name} (TASK-### ids are idempotency keys, "
                "v2 §78 row 7)"
            )
        pid = record.get("project_id")
        if (parent.parent.name == "episodes" and isinstance(pid, str)
                and parent.parent.parent.name != pid):
            problems.append(
                f"project_id: {pid} does not match the project directory "
                f"{parent.parent.parent.name} the record lives in"
            )
    if problems:
        raise Rejection(problems)
    return "VALID"


def create(envelope_path: Path, validate_only: bool = False) -> str:
    envelope = load_envelope(envelope_path)

    if "task_id" in envelope:
        raise Rejection(
            ["task_id: must NOT be supplied — task-create allocates it (§82.1)"]
        )

    # Validate with a placeholder id so schema `required` passes; the real id
    # is allocated only after validation succeeds.
    probe = dict(envelope, task_id="TASK-000")
    problems = validate(probe)
    if problems:
        raise Rejection(problems)

    if validate_only:
        return "VALID"

    episodes_dir = PROJECTS_DIR / envelope["project_id"] / "episodes"
    task_id = allocate_task_id(episodes_dir)
    task_dir = episodes_dir / task_id
    if task_dir.exists():  # defensive; allocation scans existing dirs
        raise Rejection([f"task_id: {task_id} already exists (allocation race?)"])

    final_envelope = {"task_id": task_id, **envelope}
    final_problems = validate(final_envelope)
    if final_problems:
        raise Rejection(final_problems)

    now = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    state = {
        "task_id": task_id,
        "state": "INTAKE",
        "run_id": None,
        "iteration_count": 0,
        "rejection_cycles": 0,
        "history": [
            {"at": now, "from": "NONE", "to": "INTAKE",
             "evidence": f"task-create from {envelope_path.name}"}
        ],
    }
    state_validator = Draft7Validator(json.loads(STATE_SCHEMA.read_text()))
    state_errors = [e.message for e in state_validator.iter_errors(state)]
    if state_errors:  # internal invariant, not user error
        raise RuntimeError(f"generated state.yaml invalid: {state_errors}")

    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(final_envelope, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (task_dir / "state.yaml").write_text(
        yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return task_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("envelope", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true",
                      help="pre-creation envelope: task_id must be absent")
    mode.add_argument("--validate-record", action="store_true",
                      help="post-creation record (task.yaml): task_id must "
                           "be present; nothing is written")
    args = parser.parse_args(argv)

    try:
        if args.validate_record:
            result = validate_record(args.envelope)
        else:
            result = create(args.envelope, validate_only=args.validate_only)
    except Rejection as exc:
        print("task-create: REJECTED")
        for p in exc.problems:
            print(f"  FAIL {p}")
        return EXIT_REJECTED
    print(result)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
