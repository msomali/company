#!/usr/bin/env python3
"""§88 check 12 — breaker: 1-tool-call budget halts BLOCKED, no retry loop.

Runs against TASK-002 (fixture envelope-check12-breaker.yaml,
tool_call_limit: 1, tier T2). Uses the FIXED dispatcher module from PR #65
(bootstrap/breaker-enforcement), staged at /tmp/a/b/dispatcher_fixed.py for
this run because the fix is unmerged and the episode branch must not carry
control-plane changes (PR #58 scope). sha256 of the staged module is
printed for provenance.

Sequence:
  1. action #1 (fingerprint probe:step-1) → allowed, count 1
  2. action #2 → logged as evidence, then cap breach → BLOCKED + ESC
  3. no-retry proof: action #3 refused (BLOCKED guard); dispatch() refused;
     log still shows exactly 2 action events
"""
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

EVIDENCE_DIR = Path(__file__).resolve().parent
TASK_DIR = EVIDENCE_DIR.parent
REPO_ROOT = EVIDENCE_DIR.parents[4]

FIXED = Path("/tmp/a/b/dispatcher_fixed.py")
spec = importlib.util.spec_from_file_location("dispatcher_fixed", FIXED)
dp = importlib.util.module_from_spec(spec)
sys.modules["dispatcher_fixed"] = dp
spec.loader.exec_module(dp)


class BotCommitter(dp.GitCommitter):
    def commit(self, paths, message):
        rels = [str(p.relative_to(self.repo_root)) for p in paths]
        subprocess.run(["git", "-C", str(self.repo_root), "add", *rels], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo_root),
             "-c", "user.name=agenticfoundrybot",
             "-c", "user.email=agenticfoundrybot@users.noreply.github.com",
             "commit", "-m", message],
            check=True, capture_output=True,
        )


class StubBackend:
    def spawn(self, agent_id, prompt):  # never reached — BLOCKED guard first
        raise AssertionError("spawn must not be called on a BLOCKED task")


def main() -> int:
    print(f"fixed module sha256: {hashlib.sha256(FIXED.read_bytes()).hexdigest()[:16]}")
    d = dp.Dispatcher(repo_root=REPO_ROOT, backend=StubBackend(),
                      committer=BotCommitter(REPO_ROOT))
    env = yaml.safe_load((TASK_DIR / "task.yaml").read_text())
    print(f"effective caps (wall, tools): {dp.effective_caps(env)}")

    n = d.record_action(TASK_DIR, "probe:step-1", detail="first tool action")
    print(f"action #1 allowed, count={n}")

    try:
        d.record_action(TASK_DIR, "probe:step-2", detail="second tool action")
        print("FAIL: second action did not trip the breaker")
        return 1
    except dp.DispatchError as exc:
        print(f"action #2 tripped breaker: {exc}")

    state = yaml.safe_load((TASK_DIR / "state.yaml").read_text())
    esc = TASK_DIR / "ESC-TASK-002.md"
    print(f"state: {state['state']}; ESC exists: {esc.exists()}")

    # no-retry proofs
    try:
        d.record_action(TASK_DIR, "probe:step-3")
        print("FAIL: action on BLOCKED task accepted")
        return 1
    except dp.DispatchError as exc:
        print(f"action #3 refused: {exc}")
    try:
        d.dispatch("PROJECT-000", "TASK-002")
        print("FAIL: dispatch on BLOCKED task accepted")
        return 1
    except dp.DispatchError as exc:
        print(f"dispatch refused: {exc}")

    actions = sum(
        1 for line in (TASK_DIR / "log.jsonl").read_text().splitlines()
        if '"event": "action"' in line
    )
    print(f"action events logged: {actions} (breach action retained as evidence)")
    ok = state["state"] == "BLOCKED" and esc.exists() and actions == 2
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
