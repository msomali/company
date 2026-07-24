"""ADR-B007 core lane mechanism — TaskLane worktree lifecycle (real-git,
offline) and the BOUND collector requirement (the leading test).

Bound requirement (ADR-B007 decision record, owner directive at acceptance,
2026-07-23): the episode collector scans the LANE, never the host tree. A
gate record ABSENT from the lane but PRESENT in the host clone's working
tree fails --check; the inverse (present in the lane) passes regardless of
host-tree state. A manifest must never again attest to records on no lane
ref (the PR #122 gap).
"""
import subprocess
from pathlib import Path

import yaml

import dispatcher as dp
import episode_collector as ec


def g(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         *args],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout


def _origin_and_clone(tmp_path: Path) -> tuple[Path, Path]:
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
    clone = tmp_path / "clone"
    g(tmp_path, "clone", str(origin), str(clone))
    g(clone, "config", "user.name", "dispatcher")
    g(clone, "config", "user.email", "dispatcher@company.local")
    return origin, clone


# -- TaskLane worktree lifecycle ---------------------------------------------

def test_lane_path_is_sibling_outside_the_clone(tmp_path):
    lane = dp.TaskLane(repo_root=tmp_path / "repo", branch="dispatch/TASK-5",
                       lanes_root=tmp_path / "lanes")
    assert lane.path == tmp_path / "lanes" / "TASK-5"
    # never nested inside the clone (the contamination rationale, ruling a)
    assert (tmp_path / "repo") not in lane.path.parents


def test_ensure_creates_worktree_from_origin_main(tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lanes = tmp_path / "lanes"
    lane = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-5",
                       lanes_root=lanes)
    wt = lane.ensure()
    assert wt == lanes / "TASK-5"
    assert wt.is_dir()
    assert g(wt, "rev-parse", "--abbrev-ref", "HEAD").strip() == \
        "dispatch/TASK-5"
    assert subprocess.run(
        ["git", "-C", str(wt), "merge-base", "--is-ancestor",
         "origin/main", "HEAD"]).returncode == 0


def test_commit_blobs_writes_commits_pushes_dispatcher_authored(tmp_path):
    origin, clone = _origin_and_clone(tmp_path)
    lane = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-5",
                       lanes_root=tmp_path / "lanes")
    sha = lane.commit_blobs(
        {"projects/PROJECT-000/episodes/TASK-5/state.yaml": b"task_id: TASK-5\n"},
        "TASK-5: state")
    wt = lane.path
    assert (wt / "projects/PROJECT-000/episodes/TASK-5/state.yaml"
            ).read_text() == "task_id: TASK-5\n"
    # dispatcher-authored (§80.5)
    author = g(wt, "log", "-1", "--format=%an <%ae>").strip()
    assert author == "dispatcher <dispatcher@company.local>"
    assert g(wt, "rev-parse", "HEAD").strip() == sha
    # pushed to origin
    assert "dispatch/TASK-5" in g(
        clone, "ls-remote", "origin", "refs/heads/dispatch/TASK-5")


def test_remove_prunes_worktree(tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lane = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-5",
                       lanes_root=tmp_path / "lanes")
    lane.ensure()
    assert lane.path.exists()
    lane.remove()
    assert not lane.path.exists()
    # git no longer tracks the worktree
    assert "TASK-5" not in g(clone, "worktree", "list")


def test_second_lane_does_not_cross_the_first(tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lanes = tmp_path / "lanes"
    a = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-1",
                    lanes_root=lanes)
    a.commit_blobs({"projects/PROJECT-000/episodes/TASK-1/s.yaml": b"a\n"},
                   "TASK-1")
    b = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-2",
                    lanes_root=lanes)
    b.commit_blobs({"projects/PROJECT-000/episodes/TASK-2/s.yaml": b"b\n"},
                   "TASK-2")
    # each lane sees only its own episode — no cross-contamination
    assert not (b.path / "projects/PROJECT-000/episodes/TASK-1").exists()
    assert not (a.path / "projects/PROJECT-000/episodes/TASK-2").exists()


# -- THE BOUND REQUIREMENT (leads): collector scans the lane, not the host ----

def _build_lane_episode(clone: Path, lanes: Path, gates=("SAT", "HUMAN")):
    """Materialize TASK-3's episode + gate records on its lane worktree via
    TaskLane, exactly as the dispatcher will. Returns (lane, episode_dir)."""
    lane = dp.TaskLane(repo_root=clone, branch="dispatch/TASK-3",
                       lanes_root=lanes)
    ep = "projects/PROJECT-000/episodes/TASK-3"
    state = {"task_id": "TASK-3", "state": "CLOSED",
             "history": [{"at": "2026-07-23T00:00:00Z", "from": "NONE",
                          "to": "INTAKE", "evidence": "x"}]}
    sources = {
        f"{ep}/task.yaml": b"task_id: TASK-3\n",
        f"{ep}/state.yaml": yaml.safe_dump(state).encode(),
        f"{ep}/log.jsonl": b'{"at":"t","event":"transition"}\n',
        f"{ep}/handoff.md": b"# handoff\n",
    }
    for gate in gates:
        sources[f"projects/PROJECT-000/gates/GATE-TASK-3-{gate}-1.yaml"] = (
            yaml.safe_dump({"gate_id": f"GATE-TASK-3-{gate}-1",
                            "gate_owner": gate}).encode())
    lane.commit_blobs(sources, "TASK-3: episode + gate records")
    return lane, lane.path / ep


def test_collector_reads_the_lane_and_host_records_do_not_leak(tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lanes = tmp_path / "lanes"
    lane, episode = _build_lane_episode(clone, lanes)

    manifest, problems = ec.collect(episode)
    assert problems == []
    # the manifest attests to exactly the lane's two gate records
    assert manifest["gate_records"] == [
        "gates/GATE-TASK-3-HUMAN-1.yaml",
        "gates/GATE-TASK-3-SAT-1.yaml",
    ]

    # plant a THIRD record ONLY in the host clone's working tree ...
    host_gates = clone / "projects/PROJECT-000/gates"
    host_gates.mkdir(parents=True, exist_ok=True)
    (host_gates / "GATE-TASK-3-DCE-1.yaml").write_text("gate_owner: DCE\n")
    # ... re-collecting the LANE must not see it (host tree is a different tree)
    manifest2, _ = ec.collect(episode)
    assert "gates/GATE-TASK-3-DCE-1.yaml" not in manifest2["gate_records"]


def test_check_fails_when_record_absent_from_lane_though_present_on_host(
        tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lanes = tmp_path / "lanes"
    lane, episode = _build_lane_episode(clone, lanes)
    ec.collect(episode)                       # manifest attests to SAT + HUMAN

    # the SAT record leaves the LANE but survives in the host clone tree
    host_gates = clone / "projects/PROJECT-000/gates"
    host_gates.mkdir(parents=True, exist_ok=True)
    (host_gates / "GATE-TASK-3-SAT-1.yaml").write_text("gate_owner: SAT\n")
    (lane.path / "projects/PROJECT-000/gates/GATE-TASK-3-SAT-1.yaml").unlink()

    _, problems = ec.collect(episode, check=True)
    # --check resolves through the LANE — the host copy does not rescue it
    assert any("gate record vanished from the lane" in p for p in problems)
    assert any("GATE-TASK-3-SAT-1.yaml" in p for p in problems)


def test_check_passes_when_records_present_in_lane(tmp_path):
    _, clone = _origin_and_clone(tmp_path)
    lane, episode = _build_lane_episode(clone, tmp_path / "lanes")
    ec.collect(episode)
    _, problems = ec.collect(episode, check=True)
    assert problems == []
