#!/usr/bin/env python3
"""§88 check 8 — approvals capture leg (RUNBOOK-B7.3 check-8 step 3, [A]).

Captures the owner's three decision lines from the COMMENTED review of
record (PR #58 review 4729329698, node PRR_kwDOTZyvsc8AAAABGePYIg) and
applies them via ApprovalsCapture: authorization against the §51 owner
(parsed from the register, not hardcoded), state-order enforcement, one
immutable gate record per decision, state transition per gate.

Owner instruction 2026-07-18 14:44 PDT: reference = the COMMENTED review
URL for all three records; the APPROVED (accidental, superseded) and
CHANGES_REQUESTED (cancellation-only) reviews are ignored — neither is
passed to the parser.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[4]
sys.path.insert(0, str(REPO_ROOT / "control" / "scripts"))
import approvals as ap  # noqa: E402
import dispatcher as dp  # noqa: E402

REVIEW_URL = "https://github.com/msomali/company/pull/58#pullrequestreview-4729329698"
REVIEW_BODY = "APPROVE TASK-001 SAT\nAPPROVE TASK-001 SSE\nAPPROVE TASK-001 DPC"
REVIEWER = "msomali"  # verified via API: review 4729329698 user.login


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
    owner = ap.owner_identity(REPO_ROOT)
    print(f"§51 owner of record: @{owner}")

    decisions = ap.parse_decisions(REVIEW_BODY, approver=REVIEWER,
                                   reference=REVIEW_URL)
    print(f"parsed decisions: {[(d.verb, d.task_id, d.gate) for d in decisions]}")
    assert len(decisions) == 3, "expected exactly three well-formed lines"

    d = dp.Dispatcher(repo_root=REPO_ROOT, backend=None,
                      committer=BotCommitter(REPO_ROOT))
    capture = ap.ApprovalsCapture(d, repo_root=REPO_ROOT)

    for decision in decisions:
        record_path = capture.apply("PROJECT-000", decision)
        record = yaml.safe_load(record_path.read_text())
        state = yaml.safe_load(
            (d.task_dir("PROJECT-000", "TASK-001") / "state.yaml").read_text()
        )
        ok_ref = record["approval_message_ref"] == REVIEW_URL
        print(f"APPLIED {decision.gate}: {record_path.name} "
              f"decision={record['decision']} ref_ok={ok_ref} "
              f"state_now={state['state']}")
        if not ok_ref:
            return 1

    final = yaml.safe_load(
        (d.task_dir("PROJECT-000", "TASK-001") / "state.yaml").read_text()
    )
    print(f"final state: {final['state']}")
    return 0 if final["state"] == "PRODUCTION_READINESS" else 1


if __name__ == "__main__":
    sys.exit(main())
