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
  --dispatch-once        owner-invoked one-shot dispatch (activation item 1,
                         2026-07-21). DRY-RUN by default: prints everything
                         the spawn would do plus WOULD-REFUSE reasons,
                         spawns nothing, exit 2 on any refusal condition.
                         --live performs the single real spawn (human
                         watching). The daemon NEVER dispatches — --daemon
                         constructs no backend, by code; this mode is the
                         only spawning entrypoint.

Custody: this process runs as OS user `dispatcher`, outside OpenClaw
(BA-1.4). Its credentials come from /etc/company/dispatcher.env (systemd
EnvironmentFile; names in SECRETS-MANIFEST). Nothing here prints secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

import yaml

import approvals as ap
import dispatcher as dp
import metering as mt
import session_backend as sb

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


def dispatch_once(repo_root: Path, project: str, task: str, live: bool,
                  backend_factory=None) -> int:
    """Owner-invoked one-shot dispatch (activation item 1). Dry-run unless
    ``live``; the only code path that ever constructs a spawning backend.
    ``backend_factory`` is injectable for tests (fake backend)."""
    d = dp.Dispatcher(repo_root=repo_root, backend=None)
    task_dir = d.task_dir(project, task)
    if not (task_dir / "task.yaml").is_file():
        print(f"dispatch-once: no such task {project}/{task}")
        return 2
    envelope = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    state = yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
    role = envelope["assigned_role"]

    refusals = []
    if state["state"] == "BLOCKED":
        refusals.append("task is BLOCKED — resolve the escalation first (§82.3)")
    if envelope["requested_by"] == role:
        refusals.append("separation of duties: requester == assignee (v1 §8)")
    manifest_status = None
    try:
        manifest_status = d.resolve_agent(role).get("status")
        if manifest_status != "active":
            refusals.append(
                f"manifest {role} is {manifest_status!r}, not 'active' — "
                "activation flip is the owner's act (BA-2.4)"
            )
    except dp.DispatchError as exc:
        refusals.append(str(exc))
    token_present = bool((os.environ.get(sb.TOKEN_VAR) or "").strip())
    if not token_present:
        refusals.append(
            f"{sb.TOKEN_VAR} missing from the environment "
            "(source /etc/company/dispatcher.env)"
        )

    policies_path = repo_root / "control/models/policies.yaml"
    policies = yaml.safe_load(policies_path.read_text(encoding="utf-8")) or {}
    policy_name = (policies.get("agents") or {}).get(role)
    pol = (policies.get("policies") or {}).get(policy_name) or {}
    wall_cap, tool_cap = dp.effective_caps(envelope)
    timeout_s = wall_cap * 60
    prompt = d.build_prompt(envelope)
    sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    try:
        cap = mt.SessionPool(policies_path).cap
    except mt.MeteringError:
        cap = "?"
    gateway_url = os.environ.get(sb.URL_VAR, sb.DEFAULT_GATEWAY_URL)

    mode_word = "LIVE" if live else "dry-run"
    print(f"dispatch-once ({mode_word}) {project}/{task}")
    print(f"  role: {role} (manifest status: {manifest_status})  agent id: {role.lower()}")
    print(f"  model policy: {policy_name} primary={pol.get('primary')} "
          f"fallback={pol.get('fallback')} (gateway agents.list = execution; "
          "backend passes no --model)")
    seat_cfg = os.environ.get("OPENCLAW_CONFIG_PATH")
    print(f"  seat config: OPENCLAW_CONFIG_PATH="
          f"{seat_cfg or '(unset — CLI resolves --agent from ~/.openclaw/openclaw.json of THIS user; see SOP seat-check)'}")
    print(f"  tier: {envelope['tier']}  wall cap: {wall_cap} min  "
          f"tool cap: {tool_cap}  --timeout: {timeout_s}s")
    print(f"  prompt: sha256:{sha}  bytes={len(prompt.encode('utf-8'))}")
    print(f"  gateway: {gateway_url}  token present: {'yes' if token_present else 'NO'}")
    print(f"  concurrency cap: {cap}")
    print(f"  argv: openclaw agent --agent {role.lower()} "
          f"--session-key agent:{role.lower()}:{task.lower()}-<minted-at-spawn> "
          f"--message-file <tmp> --json --timeout {timeout_s}")

    if not live:
        for r in refusals:
            print(f"  WOULD REFUSE: {r}")
        print("dispatch-once: dry-run — nothing spawned. Add --live to spawn "
              "(human watching).")
        return 2 if refusals else 0

    if refusals:
        for r in refusals:
            print(f"dispatch-once: REFUSED: {r}")
        return 1
    factory = backend_factory or sb.OpenClawSessionBackend
    backend = factory(policies_path=policies_path, timeout_seconds=timeout_s)
    live_d = dp.Dispatcher(repo_root=repo_root, backend=backend)
    try:
        run_id = live_d.dispatch(project, task)
    except (dp.DispatchError, sb.SpawnError) as exc:
        print(f"dispatch-once: FAILED: {exc}")
        return 1
    meta = (getattr(backend, "last_response", None) or {}).get("meta") or {}
    print(f"dispatch-once: spawned {run_id} durationMs={meta.get('durationMs')}")
    print("dispatch-once: transcript addressable by the session key above; "
          "run_id recorded in state.yaml and log.jsonl (committed)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--daemon", action="store_true")
    mode.add_argument("--process-review", action="store_true")
    mode.add_argument("--dispatch-once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--project")
    parser.add_argument("--task")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--approver")
    parser.add_argument("--reference")
    args = parser.parse_args(argv)

    if args.once:
        return report(args.repo_root)
    if args.dispatch_once:
        if not (args.project and args.task):
            parser.error("--dispatch-once requires --project and --task")
        return dispatch_once(args.repo_root, args.project, args.task, args.live)
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
