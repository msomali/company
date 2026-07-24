"""Delivery-path wiring: branch-pinned state commits (finding 2), turn-meta
parse across both CLI JSON shapes (finding 3), and the loud+episodic
harvest-once runtime (ADR-B006 binding requirement 1)."""
from pathlib import Path

import yaml

import dispatcher as dp
import dispatcher_runtime as rt
import harvest as hv
import session_backend as sb

from test_harvest import make_ws, valid_handoff, SpyHarvester


# -- TaskBranchCommitter (ADR-B007: worktree lane, switch retired) -----------

class FakeGit:
    """Runner(argv, cwd) for the worktree committer. File writes into the
    lane worktree are real; only git is faked."""

    def __init__(self, head_branch=False, remote_branch=False, fetch_ok=True):
        self.calls = []
        self.head_branch = head_branch
        self.remote_branch = remote_branch
        self.fetch_ok = fetch_ok

    def __call__(self, argv, cwd):
        self.calls.append(argv)
        j = " ".join(argv)
        if "rev-parse --verify --quiet refs/heads/" in j:
            return (0, "", "") if self.head_branch else (1, "", "")
        if "rev-parse --verify --quiet refs/remotes/origin/" in j:
            return (0, "", "") if self.remote_branch else (1, "", "")
        if argv[1] == "fetch":
            return (0, "", "") if self.fetch_ok else (1, "", "no network")
        if argv[1:3] == ["rev-parse", "HEAD"]:
            return 0, "deadbeefcafe1234\n", ""
        return 0, "", ""


def _commit(tmp_path, fake):
    lanes = tmp_path / "lanes"
    c = dp.TaskBranchCommitter(tmp_path, "dispatch/TASK-9", runner=fake,
                               lanes_root=lanes)
    p = tmp_path / "projects/PROJECT-000/episodes/TASK-9/state.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    c.commit([p], "msg")
    return ["\x00".join(call) for call in fake.calls], lanes


def test_new_lane_worktree_from_origin_main_then_pushed(tmp_path):
    flat, lanes = _commit(tmp_path, FakeGit())
    # brand-new lane: fetch, then worktree add -b from origin/main
    assert any("fetch\x00origin\x00main" in f for f in flat)
    assert any(f"worktree\x00add\x00-b\x00dispatch/TASK-9\x00"
               f"{lanes / 'TASK-9'}\x00origin/main" in f for f in flat)
    assert any("push\x00-u\x00origin\x00dispatch/TASK-9" in f for f in flat)
    # the CLONE checkout is never switched (retires the branch-vintage root)
    assert not any("switch" in f for f in flat)
    # ferried content materialized in the lane worktree
    assert (lanes / "TASK-9/projects/PROJECT-000/episodes/TASK-9/state.yaml"
            ).read_text() == "x"


def test_existing_local_branch_attached_not_recreated(tmp_path):
    flat, lanes = _commit(tmp_path, FakeGit(head_branch=True))
    assert any(f"worktree\x00add\x00{lanes / 'TASK-9'}\x00dispatch/TASK-9"
               in f for f in flat)
    assert not any("worktree\x00add\x00-b" in f for f in flat)
    assert not any("switch" in f for f in flat)


def test_existing_remote_branch_attached_with_reset(tmp_path):
    flat, lanes = _commit(tmp_path, FakeGit(remote_branch=True))
    assert any(f"worktree\x00add\x00-B\x00dispatch/TASK-9\x00"
               f"{lanes / 'TASK-9'}\x00origin/dispatch/TASK-9" in f
               for f in flat)


def test_present_worktree_reused_no_readd(tmp_path):
    lanes = tmp_path / "lanes"
    (lanes / "TASK-9").mkdir(parents=True)          # worktree already present
    fake = FakeGit()
    c = dp.TaskBranchCommitter(tmp_path, "dispatch/TASK-9", runner=fake,
                               lanes_root=lanes)
    p = tmp_path / "s.yaml"
    p.write_text("y")
    c.commit([p], "msg")
    flat = ["\x00".join(call) for call in fake.calls]
    assert not any("worktree\x00add" in f for f in flat)   # persistent reuse
    assert any("commit" in f for f in flat)


def test_new_lane_fetch_failure_falls_back_to_local_main_loudly(tmp_path,
                                                                capsys):
    flat, lanes = _commit(tmp_path, FakeGit(fetch_ok=False))
    assert any(f"worktree\x00add\x00-b\x00dispatch/TASK-9\x00"
               f"{lanes / 'TASK-9'}\x00main" in f for f in flat)
    assert "WARN task-lane" in capsys.readouterr().out


# -- extract_turn_meta (finding 3) --------------------------------------------

def test_meta_gateway_shape_nested_under_result():
    resp = {"status": "ok", "runId": "r",
            "result": {"payloads": [], "meta": {"durationMs": 58000}}}
    assert sb.extract_turn_meta(resp)["durationMs"] == 58000


def test_meta_embedded_shape_top_level():
    resp = {"payloads": [], "meta": {"durationMs": 1}}
    assert sb.extract_turn_meta(resp)["durationMs"] == 1


def test_meta_absent_or_malformed():
    assert sb.extract_turn_meta(None) == {}
    assert sb.extract_turn_meta({}) == {}
    assert sb.extract_turn_meta({"result": None}) == {}
    assert sb.extract_turn_meta({"result": {"meta": "bogus"}}) == {}


# -- harvest_once: loud + episodic (binding requirement 1) --------------------

class FakeCommitter:
    def __init__(self):
        self.commits = []

    def commit(self, paths, message):
        self.commits.append((list(paths), message))


def make_task(tmp_path, required_outputs):
    td = tmp_path / "projects/PROJECT-000/episodes/TASK-9"
    td.mkdir(parents=True)
    (td / "task.yaml").write_text(yaml.safe_dump({
        "task_id": "TASK-9", "project_id": "PROJECT-000",
        "assigned_role": "SDE", "requested_by": "PJM",
        "required_outputs": required_outputs,
    }))
    (td / "state.yaml").write_text(yaml.safe_dump({
        "task_id": "TASK-9", "state": "IMPLEMENTATION"}))
    return td


def harvest_dispatcher(tmp_path):
    committer = FakeCommitter()
    d = dp.Dispatcher(repo_root=tmp_path, backend=None, committer=committer)
    return d, committer


def read_events(td):
    lines = (td / "log.jsonl").read_text().strip().splitlines()
    import json
    return [json.loads(line) for line in lines]


def test_harvest_once_success_logs_and_commits_episodic_event(tmp_path, capsys):
    td = make_task(tmp_path, ["src/mod.py"])
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    d, committer = harvest_dispatcher(tmp_path)
    rc = rt.harvest_once(tmp_path, "PROJECT-000", "TASK-9", ws,
                         dispatcher=d, harvester=SpyHarvester())
    assert rc == 0
    events = [e["event"] for e in read_events(td)]
    assert "harvest_pushed" in events
    assert committer.commits and "harvested" in committer.commits[-1][1]
    assert "pushed sde/TASK-9" in capsys.readouterr().out


def test_harvest_once_refusal_is_loud_and_episodic(tmp_path, capsys):
    td = make_task(tmp_path, ["src/mod.py"])
    ws = make_ws(tmp_path, {"src/mod.py": "x\n"})   # no handoff.md
    d, committer = harvest_dispatcher(tmp_path)
    spy = SpyHarvester()
    rc = rt.harvest_once(tmp_path, "PROJECT-000", "TASK-9", ws,
                         dispatcher=d, harvester=spy)
    assert rc == 2
    assert spy.calls == []                     # nothing shipped
    events = read_events(td)
    refusal = next(e for e in events if e["event"] == "harvest_refused")
    assert "handoff.md" in refusal["reason"]   # reason recorded (req 1)
    assert committer.commits and "REFUSED" in committer.commits[-1][1]
    assert "REFUSED" in capsys.readouterr().out


def test_harvest_once_unknown_task_refuses(tmp_path, capsys):
    ws = make_ws(tmp_path, {})
    d, _ = harvest_dispatcher(tmp_path)
    rc = rt.harvest_once(tmp_path, "PROJECT-000", "TASK-404", ws, dispatcher=d)
    assert rc == 2
    assert "no such task" in capsys.readouterr().out


def test_harvest_once_unhandled_defect_still_episodic(tmp_path, monkeypatch,
                                                      capsys):
    """Finding 3 (2026-07-23): the live perms crash produced a raw traceback
    and NO episodic event. Even a defect harvest.py never anticipated must
    leave a committed harvest_error record (ADR-B006 binding req 1)."""
    td = make_task(tmp_path, ["src/mod.py"])
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    d, committer = harvest_dispatcher(tmp_path)

    def boom(**kwargs):
        raise ValueError("wholly unforeseen defect")

    monkeypatch.setattr(rt.hv, "run_harvest", boom)
    rc = rt.harvest_once(tmp_path, "PROJECT-000", "TASK-9", ws, dispatcher=d)
    assert rc == 1
    events = read_events(td)
    err = next(e for e in events if e["event"] == "harvest_error")
    assert "unhandled ValueError" in err["reason"]
    assert committer.commits and "unhandled" in committer.commits[-1][1]
    assert "FAILED (unhandled defect)" in capsys.readouterr().out


def test_harvest_once_passes_envelope_data_classification(tmp_path,
                                                          monkeypatch):
    """The stamp's sensitivity field comes from the envelope (finding 6)."""
    td = make_task(tmp_path, ["src/mod.py"])
    task = yaml.safe_load((td / "task.yaml").read_text())
    task["data_classification"] = "confidential"
    (td / "task.yaml").write_text(yaml.safe_dump(task))
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    d, _ = harvest_dispatcher(tmp_path)
    seen = {}

    def spy_run_harvest(**kwargs):
        seen.update(kwargs)
        return {"branch": "sde/TASK-9", "sha": "f" * 40, "files": []}

    monkeypatch.setattr(rt.hv, "run_harvest", spy_run_harvest)
    assert rt.harvest_once(tmp_path, "PROJECT-000", "TASK-9", ws,
                           dispatcher=d) == 0
    assert seen["data_classification"] == "confidential"
