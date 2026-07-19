#!/usr/bin/env python3
"""§88 check 9 — HUMAN gate capture (RUNBOOK-B7.3 check-9 step 5).

Single decision from COMMENTED review 4729388103 on release PR #61
(user msomali, verified via API 2026-07-18): `APPROVE TASK-001 HUMAN`.
Expected: immutable record GATE-TASK-001-HUMAN-1.yaml; state
HUMAN_RELEASE_AUTHORIZATION → DEPLOYMENT. Captured BEFORE the owner's
merge so the record of authorization precedes the release act.
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

REVIEW_URL = "https://github.com/msomali/company/pull/61#pullrequestreview-4729388103"
REVIEW_BODY = "APPROVE TASK-001 HUMAN"
REVIEWER = "msomali"


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
    decisions = ap.parse_decisions(REVIEW_BODY, approver=REVIEWER,
                                   reference=REVIEW_URL)
    print(f"parsed: {[(x.verb, x.task_id, x.gate) for x in decisions]}")
    assert len(decisions) == 1 and decisions[0].gate == "HUMAN"

    d = dp.Dispatcher(repo_root=REPO_ROOT, backend=None,
                      committer=BotCommitter(REPO_ROOT))
    capture = ap.ApprovalsCapture(d, repo_root=REPO_ROOT)
    record_path = capture.apply("PROJECT-000", decisions[0])
    record = yaml.safe_load(record_path.read_text())
    state = yaml.safe_load(
        (d.task_dir("PROJECT-000", "TASK-001") / "state.yaml").read_text()
    )
    print(f"record: {record_path.name} gate_owner={record['gate_owner']} "
          f"decision={record['decision']} "
          f"ref_ok={record['approval_message_ref'] == REVIEW_URL}")
    print(f"final state: {state['state']}")
    return 0 if state["state"] == "DEPLOYMENT" else 1


if __name__ == "__main__":
    sys.exit(main())
