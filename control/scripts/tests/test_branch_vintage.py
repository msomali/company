"""Branch vintage (owner finding 1, 2026-07-23) — real-git verification,
now against the ADR-B007 worktree lane.

The old defect: a dispatch-branch checkout reverted the clone's
control/scripts to branch vintage, because the committer SWITCHED the clone
to the lane branch. ADR-B007 retires the switch: state commits land in a
persistent lane WORKTREE sibling to the clone, and the clone's own checkout
is never touched. This test pins both halves of the resulting property:

  1. The clone's checkout is NEVER switched by a state commit — so it cannot
     revert to a branch's tooling (the finding's root, now structurally
     impossible).
  2. A freshly minted lane worktree carries CURRENT origin/main vintage
     (committer-minted branches base on fetched origin/main), even when the
     clone's local main is stale.
  3. A reused lane keeps its creation-time vintage (worktrees are persistent,
     never silently rebased) — which is why the SOP's return-to-main rule for
     long-lived lanes stays operational, not just structural.

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


def _origin_with_scripts_v1(tmp_path: Path) -> tuple[Path, Path]:
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
    return origin, seed


def _clone(tmp_path: Path, origin: Path, name: str) -> Path:
    clone = tmp_path / name
    g(tmp_path, "clone", str(origin), str(clone))
    g(clone, "config", "user.name", "dispatcher")
    g(clone, "config", "user.email", "dispatcher@company.local")
    return clone


def test_clone_never_switched_lane_worktree_carries_current_origin_main(
        tmp_path):
    origin, seed = _origin_with_scripts_v1(tmp_path)
    clone = _clone(tmp_path, origin, "dispatcher-clone")

    # main advances to v2 AFTER the clone froze at v1.
    (seed / "control/scripts/tool.py").write_text("VERSION = 2\n")
    g(seed, "commit", "-am", "scripts v2")
    g(seed, "push")
    assert (clone / "control/scripts/tool.py").read_text() == "VERSION = 1\n"
    clone_head_before = g(clone, "rev-parse", "--abbrev-ref", "HEAD").strip()

    # A state commit on the lane, via the worktree committer.
    lanes = tmp_path / "lanes"
    state = clone / "projects/PROJECT-000/episodes/TASK-777/state.yaml"
    state.parent.mkdir(parents=True)
    state.write_text("task_id: TASK-777\n")
    dp.TaskBranchCommitter(clone, "dispatch/TASK-777",
                           lanes_root=lanes).commit([state], "TASK-777: state")

    # (1) the clone's own checkout is untouched — still on its branch, still v1
    assert g(clone, "rev-parse", "--abbrev-ref", "HEAD").strip() == \
        clone_head_before
    assert (clone / "control/scripts/tool.py").read_text() == "VERSION = 1\n"

    # (2) the lane worktree carries CURRENT origin/main (v2), sibling to clone
    lane = lanes / "TASK-777"
    assert (lane / "control/scripts/tool.py").read_text() == "VERSION = 2\n"
    assert g(lane, "rev-parse", "--abbrev-ref", "HEAD").strip() == \
        "dispatch/TASK-777"
    assert subprocess.run(
        ["git", "-C", str(lane), "merge-base", "--is-ancestor",
         "origin/main", "HEAD"]).returncode == 0
    # pushed
    assert "dispatch/TASK-777" in g(
        clone, "ls-remote", "origin", "refs/heads/dispatch/TASK-777")
    # the ferried state file is committed in the lane
    assert (lane / "projects/PROJECT-000/episodes/TASK-777/state.yaml"
            ).read_text() == "task_id: TASK-777\n"


def test_reused_lane_keeps_creation_vintage(tmp_path):
    origin, seed = _origin_with_scripts_v1(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    lanes = tmp_path / "lanes"

    s1 = clone / "s1.txt"
    s1.write_text("one\n")
    c = dp.TaskBranchCommitter(clone, "dispatch/TASK-778", lanes_root=lanes)
    c.commit([s1], "TASK-778: first")

    # main advances after the lane worktree was minted
    (seed / "control/scripts/tool.py").write_text("VERSION = 2\n")
    g(seed, "commit", "-am", "v2")
    g(seed, "push")

    s2 = clone / "s2.txt"
    s2.write_text("two\n")
    c.commit([s2], "TASK-778: second")

    lane = lanes / "TASK-778"
    # persistent worktree reused: still creation-time vintage (v1), not rebased
    assert (lane / "control/scripts/tool.py").read_text() == "VERSION = 1\n"
    # both ferried files are present and committed on the lane
    assert (lane / "s1.txt").read_text() == "one\n"
    assert (lane / "s2.txt").read_text() == "two\n"
    # clone still pristine
    assert g(clone, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
