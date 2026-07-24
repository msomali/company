"""task-create commit-at-creation (ADR-B007 ruling b) — real git, offline.

The never-committed task.yaml finding is closed at the source: the fresh
episode is written INTO the task's lane worktree and committed+pushed, so it
exists on a ref from creation. No clone-tree copy is made.
"""
import subprocess
from pathlib import Path

import pytest
import yaml

import dispatcher as dp
import task_create as tc

REPO = Path(__file__).resolve().parents[3]

VALID = {
    "project_id": "PROJECT-000",
    "requested_by": "PJM",
    "assigned_role": "SDE",
    "objective": "Implement titlecase per charter.",
    "risk_class": "low",
    "tier": "T1",
    "data_classification": "internal",
    "acceptance_criteria": ["artifact exists"],
    "required_outputs": ["projects/PROJECT-000/src/x.py"],
    "priority": "medium",
    "budgets": {"wall_clock_minutes": 30, "tool_call_limit": 25,
                "model_budget_tag": "t"},
}


def g(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         *args], cwd=str(cwd), check=True, capture_output=True, text=True).stdout


@pytest.fixture
def clone(tmp_path, monkeypatch):
    (tmp_path / "control/schemas").mkdir(parents=True)
    for name in ("task.json", "state.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text())
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)
    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")

    origin = tmp_path / "origin.git"
    origin.mkdir()
    g(origin, "init", "--bare", "--initial-branch=main", ".")
    seed = tmp_path / "seed"
    g(tmp_path, "clone", str(origin), str(seed))
    (seed / "README.md").write_text("seed\n")
    g(seed, "checkout", "-b", "main")
    g(seed, "add", "-A")
    g(seed, "commit", "-m", "init")
    g(seed, "push", "-u", "origin", "main")
    clone_dir = tmp_path / "clone"
    g(tmp_path, "clone", str(origin), str(clone_dir))
    g(clone_dir, "config", "user.name", "dispatcher")
    g(clone_dir, "config", "user.email", "dispatcher@company.local")
    return tmp_path, clone_dir


def _env(sandbox, data=None):
    p = sandbox / "e.yaml"
    p.write_text(yaml.safe_dump(data or VALID))
    return p


def test_commit_lane_writes_episode_onto_the_lane_committed(clone):
    sandbox, clone_dir = clone
    lanes = sandbox / "lanes"
    tid = tc.create(_env(sandbox), commit_lane=True, repo_root=clone_dir,
                    lanes_root=lanes)
    assert tid == "TASK-001"
    lane = lanes / "TASK-001"
    ep = lane / "projects/PROJECT-000/episodes/TASK-001"
    # episode present in the lane worktree ...
    assert yaml.safe_load((ep / "task.yaml").read_text())["task_id"] == "TASK-001"
    assert yaml.safe_load((ep / "state.yaml").read_text())["state"] == "INTAKE"
    # ... and TRACKED ON A REF (committed to the lane branch), the whole point
    tracked = g(lane, "ls-files",
                "projects/PROJECT-000/episodes/TASK-001/task.yaml")
    assert tracked.strip().endswith("task.yaml")
    # dispatcher-authored, pushed
    assert g(lane, "log", "-1", "--format=%an").strip() == "dispatcher"
    assert "dispatch/TASK-001" in g(
        clone_dir, "ls-remote", "origin", "refs/heads/dispatch/TASK-001")
    # NO clone-tree copy (lane is the only home)
    assert not (sandbox / "projects/PROJECT-000/episodes/TASK-001").exists()


def test_allocation_accounts_for_active_lanes(clone):
    sandbox, clone_dir = clone
    lanes = sandbox / "lanes"
    a = tc.create(_env(sandbox), commit_lane=True, repo_root=clone_dir,
                  lanes_root=lanes)
    b = tc.create(_env(sandbox), commit_lane=True, repo_root=clone_dir,
                  lanes_root=lanes)
    assert (a, b) == ("TASK-001", "TASK-002")   # second sees the first's lane


def test_rejected_envelope_creates_no_lane(clone):
    sandbox, clone_dir = clone
    bad = dict(VALID)
    del bad["objective"]
    with pytest.raises(tc.Rejection):
        tc.create(_env(sandbox, bad), commit_lane=True, repo_root=clone_dir,
                  lanes_root=sandbox / "lanes")
    assert not (sandbox / "lanes").exists()      # nothing minted on rejection
