#!/usr/bin/env python3
"""§88 check 8 prerequisite — evidenced state-walk of TASK-001 to
QUALITY_REVIEW (RUNBOOK-B7.3 check-8 step 1, [A] leg).

Walks the Appendix A forward chain via dispatcher.transition(): every edge
validates legality, appends history with a real-artifact evidence string,
writes state.yaml, appends log.jsonl, and commits (§82.4/§82.6). Committer
is GitCommitter with the ADR-B000 bot identity pinned per commit.

No model call, no backend, no manifest read — transition() only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[4]
sys.path.insert(0, str(REPO_ROOT / "control" / "scripts"))
import dispatcher as dp  # noqa: E402


class BotCommitter(dp.GitCommitter):
    """GitCommitter with explicit ADR-B000 identity (sandbox has no global
    git identity; TOOLS.md mandates per-commit -c flags)."""

    def commit(self, paths, message):
        rels = [str(p.relative_to(self.repo_root)) for p in paths]
        subprocess.run(
            ["git", "-C", str(self.repo_root), "add", *rels], check=True
        )
        subprocess.run(
            ["git", "-C", str(self.repo_root),
             "-c", "user.name=agenticfoundrybot",
             "-c", "user.email=agenticfoundrybot@users.noreply.github.com",
             "commit", "-m", message],
            check=True, capture_output=True,
        )


# Edge → evidence citing the artifact that genuinely discharges it.
WALK = [
    ("DISCOVERY",
     "dispatch executed check 3: recorded-run-001, prompt capture "
     "evidence/check3-dispatch-prompt.txt (digest+envelope+links verified)"),
    ("REQUIREMENTS",
     "acceptance criteria fixed in task.yaml: unicode folding, separator "
     "trimming, deterministic property tests (envelope of record)"),
    ("DESIGN",
     "design recorded: notes/slugify-implementation.md 'Approach' (NFKD "
     "fold + ascii round-trip + single-regex collapse), merged via PR #53"),
    ("DELIVERY_PLAN",
     "delivery plan = PR #53 handoff package sections 1-4 (branch "
     "sde/TASK-001-slugify, opened 2026-07-18)"),
    ("IMPLEMENTATION",
     "implementation commits b3a22a2..a31c274d on PR #53: src/slugify.py + "
     "tests/test_slugify.py (516 tests initial, 521 after SAT-53-F1)"),
    ("QUALITY_REVIEW",
     "521/521 tests green at a31c274d; SAT review opened: cycle-1 record "
     "PR #53 comment 5012331464 (evidence/check5-sat-two-cycle.md)"),
]


def main() -> int:
    d = dp.Dispatcher(
        repo_root=REPO_ROOT, backend=None, committer=BotCommitter(REPO_ROOT)
    )
    task_dir = d.task_dir("PROJECT-000", "TASK-001")
    for to_state, evidence in WALK:
        state = d.transition(task_dir, to_state, evidence=evidence)
        print(f"OK {state['history'][-1]['from']} -> {to_state}")
    final = d._read(task_dir, "state.yaml")
    print(f"final state: {final['state']}")
    print(f"history entries: {len(final['history'])}")
    return 0 if final["state"] == "QUALITY_REVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
