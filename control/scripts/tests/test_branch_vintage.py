"""Branch vintage (owner finding 1, 2026-07-23) — real-git verification.

A dispatch-branch checkout reverts control/scripts/ to the branch's vintage:
the clone at /srv/company/repo is BOTH the code the runtime executes and the
state-lane working tree, so whatever branch it sits on IS the tooling. The
live cycle hit this through the legacy dispatch/TASK-003 (minted before
TaskBranchCommitter existed, based on an old main — no harvest code at all;
the owner hand-synced, commit 046fe2b).

This test pins the property that makes committer-minted branches immune AT
CREATION: TaskBranchCommitter bases new branches on freshly FETCHED
origin/main, so a dispatch branch minted today carries today's scripts even
when the clone's local main is stale. (It freezes at creation time — the
operational leg, returning the clone to current main before invoking tools,
is SOP: 'Code vintage' in dispatcher-install.md.)

Offline: 'origin' is a local bare repo; no network involved.
"""
import subprocess
from pathlib import Path

import dispatcher as dp


def g(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         *args],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return proc.stdout


def test_minted_dispatch_branch_carries_current_origin_main_scripts(tmp_path):
    origin = tmp_path / "origin.git"
    origin.mkdir()
    g(origin, "init", "--bare", "--initial-branch=main", ".")

    seed = tmp_path / "seed"
    g(tmp_path, "clone", str(origin), str(seed))
    scripts = seed / "control" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "tool.py").write_text("VERSION = 1\n")
    g(seed, "checkout", "-b", "main")
    g(seed, "add", "-A")
    g(seed, "commit", "-m", "scripts v1")
    g(seed, "push", "-u", "origin", "main")

    # The dispatcher clone freezes at v1 ...
    clone = tmp_path / "dispatcher-clone"
    g(tmp_path, "clone", str(origin), str(clone))
    g(clone, "config", "user.name", "dispatcher")
    g(clone, "config", "user.email", "dispatcher@company.local")

    # ... and main advances afterwards.
    (scripts / "tool.py").write_text("VERSION = 2\n")
    g(seed, "commit", "-am", "scripts v2")
    g(seed, "push")
    assert (clone / "control/scripts/tool.py").read_text() == "VERSION = 1\n"

    # State-lane commit on a branch the committer must mint fresh.
    state = clone / "projects/PROJECT-000/episodes/TASK-777/state.yaml"
    state.parent.mkdir(parents=True)
    state.write_text("task_id: TASK-777\n")
    dp.TaskBranchCommitter(clone, "dispatch/TASK-777").commit(
        [state], "TASK-777: state")

    # The minted branch checkout carries CURRENT origin/main's scripts —
    # not the clone's stale local vintage.
    assert (clone / "control/scripts/tool.py").read_text() == "VERSION = 2\n"
    head = g(clone, "rev-parse", "--abbrev-ref", "HEAD").strip()
    assert head == "dispatch/TASK-777"
    # Based on origin/main (v2), and pushed.
    assert subprocess.run(
        ["git", "-C", str(clone), "merge-base", "--is-ancestor",
         "origin/main", "HEAD"],
    ).returncode == 0
    remote = g(clone, "ls-remote", "origin", "refs/heads/dispatch/TASK-777")
    assert "dispatch/TASK-777" in remote


def test_existing_branch_vintage_is_not_silently_rewritten(tmp_path):
    """The immunity is AT CREATION only: an existing dispatch branch keeps
    its vintage (reused, never rebased by the committer) — that residual is
    exactly why the SOP's return-to-main rule is unconditional."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    g(origin, "init", "--bare", "--initial-branch=main", ".")
    seed = tmp_path / "seed"
    g(tmp_path, "clone", str(origin), str(seed))
    (seed / "tool.py").write_text("VERSION = 1\n")
    g(seed, "checkout", "-b", "main")
    g(seed, "add", "-A")
    g(seed, "commit", "-m", "v1")
    g(seed, "push", "-u", "origin", "main")

    clone = tmp_path / "clone"
    g(tmp_path, "clone", str(origin), str(clone))
    g(clone, "config", "user.name", "dispatcher")
    g(clone, "config", "user.email", "dispatcher@company.local")

    s1 = clone / "s1.txt"
    s1.write_text("one\n")
    c = dp.TaskBranchCommitter(clone, "dispatch/TASK-778")
    c.commit([s1], "TASK-778: first")

    # main advances after the branch was minted
    (seed / "tool.py").write_text("VERSION = 2\n")
    g(seed, "commit", "-am", "v2")
    g(seed, "push")

    s2 = clone / "s2.txt"
    s2.write_text("two\n")
    c.commit([s2], "TASK-778: second")
    # Reused branch: still the creation-time vintage — by design.
    assert (clone / "tool.py").read_text() == "VERSION = 1\n"
