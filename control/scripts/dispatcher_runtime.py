#!/usr/bin/env python3
"""Dispatcher runtime entrypoint (B4.3) — the process the systemd unit runs.

Thin, auditable shell around the B4.2 library modules. Modes:

  --once                 scan all projects' episodes; print a status report
                         (task, state, run_id, queue/cap); NO side effects.
  --process-review       read a review/message body on stdin, parse decision
                         lines (approvals.parse_decisions), authorize against
                         the §51 owner register, apply each decision. This is
                         the interim §51 channel feed; a dedicated #approvals
                         channel later replaces the transport, not the logic.
  --daemon --interval N  loop --once every N seconds (idle heartbeat during
                         bootstrap: every manifest is contract-only, so
                         dispatch structurally refuses — BA-2.4).

Custody: this process runs as OS user `dispatcher`, outside OpenClaw
(BA-1.4). Its credentials come from /etc/company/dispatcher.env (systemd
EnvironmentFile; names in SECRETS-MANIFEST). Nothing here prints secrets.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

import approvals as ap
import dispatcher as dp
import metering as mt

REPO_ROOT = Path(__file__).resolve().parents[2]


def scan(repo_root: Path) -> list[dict]:
    rows = []
    projects = repo_root / "projects"
    if not projects.exists():
        return rows
    for episodes in sorted(projects.glob("PROJECT-*/episodes")):
        for task_dir in sorted(episodes.glob("TASK-*")):
            state_file = task_dir / "state.yaml"
            if not state_file.exists():
                continue
            state = yaml.safe_load(state_file.read_text(encoding="utf-8"))
            rows.append({
                "project": episodes.parent.name,
                "task": state.get("task_id", task_dir.name),
                "state": state.get("state"),
                "run_id": state.get("run_id"),
                "rejection_cycles": state.get("rejection_cycles", 0),
            })
    return rows


def report(repo_root: Path) -> int:
    rows = scan(repo_root)
    try:
        pool = mt.SessionPool(repo_root / "control/models/policies.yaml")
        cap = pool.cap
    except mt.MeteringError as exc:
        print(f"WARN concurrency: {exc}")
        cap = None
    print(f"dispatcher: {len(rows)} task(s); concurrency cap={cap}")
    for r in rows:
        print(f"  {r['project']}/{r['task']}: {r['state']}"
              f" run_id={r['run_id']} rejections={r['rejection_cycles']}")
    return 0


def process_review(repo_root: Path, project: str, approver: str,
                   reference: str, body: str) -> int:
    d = dp.Dispatcher(repo_root=repo_root, backend=None)
    capture = ap.ApprovalsCapture(d, repo_root=repo_root)
    decisions = ap.parse_decisions(body, approver=approver, reference=reference)
    if not decisions:
        print("no well-formed decision lines found; nothing applied "
              "(no inference — §51)")
        return 0
    failures = 0
    for decision in decisions:
        try:
            record = capture.apply(project, decision)
            print(f"applied: {decision.verb} {decision.task_id} "
                  f"{decision.gate} -> {record.name}")
        except ap.ApprovalError as exc:
            failures += 1
            print(f"refused: {decision.verb} {decision.task_id} "
                  f"{decision.gate}: {exc}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--daemon", action="store_true")
    mode.add_argument("--process-review", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--project")
    parser.add_argument("--approver")
    parser.add_argument("--reference")
    args = parser.parse_args(argv)

    if args.once:
        return report(args.repo_root)
    if args.process_review:
        if not (args.project and args.approver and args.reference):
            parser.error("--process-review requires --project, --approver, "
                         "--reference")
        body = sys.stdin.read()
        return process_review(args.repo_root, args.project, args.approver,
                              args.reference, body)
    while True:  # --daemon
        report(args.repo_root)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
