#!/usr/bin/env python3
"""§88 check 13 — post-resume re-dispatch leg (RUNBOOK-B7.2 v1.8, step 5).

Runs in a FRESH session after the kill-switch pause/resume cycle
(owner pause 2026-07-18 ~20:32 PDT; resume ~20:47 PDT; the prior bot
session died with the gateway). This process has no in-memory continuity:
everything it knows about TASK-001 comes from the committed
state.yaml/task.yaml.

Legs:
  1. Re-dispatch from persisted state: Dispatcher with the REAL repo root
     (real state.yaml is the source AND the target), manifest_dir pointed
     at a TemporaryDirectory copy with sde.yaml flipped active (check-3
     BA-2.4-safe pattern — real manifests untouched), recording backend
     (P2 option b; returns run_id recorded-resume-001), bot committer.
     Asserts: run_id null → recorded-resume-001; iteration_count 0 → 1;
     the 14-entry pre-pause history preserved verbatim (continuity from
     disk, not memory); dispatch event logged; prompt captured.
  2. Completion: evidenced transitions DEPLOYMENT → PRODUCTION_VERIFICATION
     → OPERATIONS_AND_FEEDBACK → CLOSED (terminal; "completes" under
     P2(b)).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

EVIDENCE_DIR = Path(__file__).resolve().parent
TASK_DIR = EVIDENCE_DIR.parent
REPO_ROOT = EVIDENCE_DIR.parents[4]
sys.path.insert(0, str(REPO_ROOT / "control" / "scripts"))
import dispatcher as dp  # noqa: E402


class RecordingBackend:
    def __init__(self):
        self.spawned = []

    def spawn(self, agent_id, prompt):
        self.spawned.append((agent_id, prompt))
        return "recorded-resume-001"


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


def main() -> int:
    pre = yaml.safe_load((TASK_DIR / "state.yaml").read_text())
    pre_history = list(pre["history"])
    print(f"pre-dispatch (from disk): state={pre['state']} "
          f"run_id={pre['run_id']} iteration={pre['iteration_count']} "
          f"history_entries={len(pre_history)}")
    assert pre["state"] == "DEPLOYMENT" and pre["run_id"] is None

    with tempfile.TemporaryDirectory() as td:
        scratch_manifests = Path(td) / "manifests"
        shutil.copytree(REPO_ROOT / "control/manifests", scratch_manifests)
        sde = scratch_manifests / "sde.yaml"
        m = yaml.safe_load(sde.read_text())
        m["status"] = "active"  # scratch copy only (BA-2.4)
        sde.write_text(yaml.safe_dump(m, sort_keys=False))

        backend = RecordingBackend()
        d = dp.Dispatcher(repo_root=REPO_ROOT, backend=backend,
                          committer=BotCommitter(REPO_ROOT),
                          manifest_dir=scratch_manifests)
        run_id = d.dispatch("PROJECT-000", "TASK-001")
        agent_id, prompt = backend.spawned[0]
        (EVIDENCE_DIR / "check13-redispatch-prompt.txt").write_text(prompt)

    post = yaml.safe_load((TASK_DIR / "state.yaml").read_text())
    checks = {
        "run_id recorded": post["run_id"] == run_id == "recorded-resume-001",
        "iteration 0->1": post["iteration_count"] == 1,
        "history preserved": post["history"] == pre_history,
        "prompt has envelope from disk": "task_id: TASK-001" in prompt
        and "slugify(title)" in prompt,
    }
    for name, ok in checks.items():
        print(f"observable: {name}: {'PASS' if ok else 'FAIL'}")
    if not all(checks.values()):
        return 1
    print(f"re-dispatched to {agent_id} [{run_id}] from persisted state")

    # -- completion leg -----------------------------------------------------
    walk = [
        ("PRODUCTION_VERIFICATION",
         "release merged by owner: PR #61, merge f9bb463b; release branch "
         "carries slugify v1.0 + notes (GATE-TASK-001-HUMAN-1 lineage)"),
        ("OPERATIONS_AND_FEEDBACK",
         "episode evidence complete through check 12; cost report shows "
         "task usage post-#63 fix (3456/2531 tok, 0.16111 USD)"),
        ("CLOSED",
         "\u00a788 dry-run task complete: checks 1-12 evidenced in this episode; "
         "custody drill (check 13) closes the task \u2014 terminal state"),
    ]
    for to_state, evidence in walk:
        state = d.transition(TASK_DIR, to_state, evidence=evidence)
        print(f"OK -> {to_state}")
    final = yaml.safe_load((TASK_DIR / "state.yaml").read_text())
    print(f"final state: {final['state']} "
          f"(terminal: {dp.legal_transitions(final['state']) == set()}) "
          f"history_entries={len(final['history'])}")
    return 0 if final["state"] == "CLOSED" else 1


if __name__ == "__main__":
    sys.exit(main())
