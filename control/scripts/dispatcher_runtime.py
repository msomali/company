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
  --harvest-once         post-turn delivery harvest (ADR-B006): collect
                         required_outputs from the role workspace onto
                         <role>/TASK-###; every outcome episodic.
  --transition           owner-invoked single §82.4 state transition with
                         mandatory evidence (added 2026-07-23, delivery-
                         cycle item 7). --process-review covers exactly the
                         six gate edges; the INTAKE→…→QUALITY_REVIEW walk
                         and the DEPLOYMENT→…→CLOSED tail previously had
                         no sanctioned CLI — TASK-001's §88 walk used
                         bespoke drivers. Same Dispatcher.transition()
                         authority as every other path: illegal edges
                         refuse, BLOCKED-resume rules hold, the onboarded-
                         T3 rule fires at DEPLOYMENT, and the write commits
                         to dispatch/TASK-### (finding 2). HARD INTERLOCK
                         (owner ruling 2026-07-23): leaving a gate-owned
                         state is a gate decision — --transition REFUSES it
                         and names --process-review, the only path that
                         writes the immutable gate record WITH the
                         transition. Gate records are structurally
                         unskippable, not procedurally. Sole exemption:
                         --to BLOCKED (escalation is not a gate decision).
                         The daemon still never transitions anything.

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
import harvest as hv
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
        # Finding 2 (2026-07-22): every state-writing path targets the task's
        # dispatch branch explicitly — never the clone's ambient checkout.
        d.committer = dp.TaskBranchCommitter(
            repo_root, f"dispatch/{decision.task_id}")
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
                  backend_factory=None, workspace: Path | None = None) -> int:
    """Owner-invoked one-shot dispatch (activation item 1). Dry-run unless
    ``live``; the only code path that ever constructs a spawning backend.
    ``backend_factory`` is injectable for tests (fake backend). When
    ``workspace`` is given, a successful live turn is followed by the
    ADR-B006 delivery harvest; without it the skip is printed loudly."""
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
    print(f"  state lane: dispatch/{task} (explicit — finding 2)  "
          f"delivery lane: {role.lower()}/{task}  "
          f"workspace: {workspace or '(none — harvest will be skipped LOUDLY)'}")

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
    live_d = dp.Dispatcher(
        repo_root=repo_root, backend=backend,
        committer=dp.TaskBranchCommitter(repo_root, f"dispatch/{task}"),
    )
    try:
        run_id = live_d.dispatch(project, task)
    except (dp.DispatchError, sb.SpawnError) as exc:
        print(f"dispatch-once: FAILED: {exc}")
        return 1
    meta = sb.extract_turn_meta(getattr(backend, "last_response", None))
    print(f"dispatch-once: spawned {run_id} durationMs={meta.get('durationMs')}")
    print(f"dispatch-once: transcript addressable by the session key above; "
          f"run_id recorded in state.yaml and log.jsonl (dispatch/{task})")
    if workspace is None:
        print(f"delivery: NOT harvested — no --workspace given. Run "
              f"--harvest-once --project {project} --task {task} "
              f"--workspace <role workspace> (ADR-B006 req 1: skips are "
              f"loud, never silent)")
        return 0
    return harvest_once(repo_root, project, task, workspace,
                        dispatcher=live_d)


# The six gate-owned states, derived from the approvals module (single
# source of truth): state → the gate whose decision is the ONLY sanctioned
# exit. Appendix-A legality is necessary but not sufficient here — a legal
# edge out of one of these states without a gate record is exactly the
# bypass the 2026-07-23 owner ruling forbids.
GATE_OWNED_STATES = {
    expected: gate for gate, (expected, _to) in ap.GATE_TRANSITIONS.items()
}


def transition_once(repo_root: Path, project: str, task: str, to: str,
                    evidence: str) -> int:
    """Owner-invoked single state transition (§82.4 machine authority).
    Every legality rule lives in Dispatcher.transition(); this is transport
    plus the branch-pinned committer — exactly the --process-review
    precedent — plus the gate interlock: exits from gate-owned states
    refuse (approve AND reject targets alike; a rejection without its
    record would skip the gate history and the rejection-cycle counter
    just as surely). Only BLOCKED, escalation, passes."""
    d = dp.Dispatcher(
        repo_root=repo_root, backend=None,
        committer=dp.TaskBranchCommitter(repo_root, f"dispatch/{task}"),
    )
    task_dir = d.task_dir(project, task)
    if not (task_dir / "state.yaml").is_file():
        print(f"transition: no such task {project}/{task}")
        return 2
    frm = yaml.safe_load(
        (task_dir / "state.yaml").read_text(encoding="utf-8")
    ).get("state")
    gate = GATE_OWNED_STATES.get(frm)
    if gate and to != "BLOCKED":
        print(
            f"transition: REFUSED: {frm} is gate-owned — leaving it is the "
            f"{gate} gate's decision, and gate records are structurally "
            f"unskippable (owner ruling 2026-07-23). Use --process-review "
            f"with 'APPROVE {task} {gate} — <evidence>' (or REJECT) so the "
            f"immutable GATE-{task}-{gate}-# record is written with the "
            f"transition. Only --to BLOCKED (escalation) leaves a gate "
            f"state through this mode."
        )
        return 2
    try:
        state = d.transition(task_dir, to, evidence=evidence)
    except dp.DispatchError as exc:
        print(f"transition: REFUSED: {exc}")
        return 2
    print(f"transition: {task} → {state['state']} "
          f"(history+log committed to dispatch/{task})")
    return 0


def harvest_once(repo_root: Path, project: str, task: str, workspace,
                 slug: str | None = None, dispatcher=None,
                 harvester=None) -> int:
    """Post-turn delivery harvest (ADR-B006): collect required_outputs from
    the role workspace, refuse loudly on any defect, land the product on
    <role>/TASK-### and the episodic record on dispatch/TASK-###. Every
    outcome — success, refusal, error — is a committed log.jsonl event
    (binding requirement 1: never a silent no-op)."""
    d = dispatcher or dp.Dispatcher(
        repo_root=repo_root, backend=None,
        committer=dp.TaskBranchCommitter(repo_root, f"dispatch/{task}"),
    )
    task_dir = d.task_dir(project, task)
    if not (task_dir / "task.yaml").is_file():
        print(f"harvest-once: no such task {project}/{task}")
        return 2
    envelope = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    role = envelope["assigned_role"]
    try:
        result = hv.run_harvest(
            repo_root=repo_root,
            workspace=Path(workspace),
            project_id=project,
            task_id=task,
            role=role,
            required_outputs=list(envelope.get("required_outputs") or []),
            slug=slug,
            harvester=harvester,
        )
    except hv.HarvestRefused as exc:
        log_path = d.log(task_dir, "harvest_refused", reason=str(exc))
        d.committer.commit(
            [log_path],
            f"{task}: harvest REFUSED — episodic record (ADR-B006 req 1)",
        )
        print(f"harvest-once: REFUSED: {exc}")
        return 2
    except hv.HarvestError as exc:
        log_path = d.log(task_dir, "harvest_error", reason=str(exc))
        d.committer.commit(
            [log_path], f"{task}: harvest ERROR — episodic record")
        print(f"harvest-once: FAILED: {exc}")
        return 1
    log_path = d.log(task_dir, "harvest_pushed", branch=result["branch"],
                     sha=result["sha"], files=result["files"])
    d.committer.commit(
        [log_path],
        f"{task}: delivery harvested to {result['branch']} @ {result['sha'][:9]}",
    )
    print(f"harvest-once: pushed {result['branch']} @ {result['sha'][:9]} "
          f"({len(result['files'])} file(s), incl. handoff)")
    print("harvest-once: delivery.yml opens/updates the PR as the bot from "
          "the agent handoff; a red run there is a validation-drift finding")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--daemon", action="store_true")
    mode.add_argument("--process-review", action="store_true")
    mode.add_argument("--dispatch-once", action="store_true")
    mode.add_argument("--harvest-once", action="store_true")
    mode.add_argument("--transition", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--project")
    parser.add_argument("--task")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workspace", type=Path,
                        help="role agent workspace to harvest (ADR-B006)")
    parser.add_argument("--slug", help="optional delivery-branch suffix")
    parser.add_argument("--approver")
    parser.add_argument("--reference")
    parser.add_argument("--to", help="target state (§82.4 Appendix A name)")
    parser.add_argument("--evidence",
                        help="mandatory transition evidence (§82.4)")
    args = parser.parse_args(argv)

    if args.once:
        return report(args.repo_root)
    if args.dispatch_once:
        if not (args.project and args.task):
            parser.error("--dispatch-once requires --project and --task")
        return dispatch_once(args.repo_root, args.project, args.task,
                             args.live, workspace=args.workspace)
    if args.harvest_once:
        if not (args.project and args.task and args.workspace):
            parser.error("--harvest-once requires --project, --task, "
                         "--workspace")
        return harvest_once(args.repo_root, args.project, args.task,
                            args.workspace, slug=args.slug)
    if args.transition:
        if not (args.project and args.task and args.to
                and args.evidence is not None):
            parser.error("--transition requires --project, --task, --to, "
                         "--evidence")
        return transition_once(args.repo_root, args.project, args.task,
                               args.to, args.evidence)
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
