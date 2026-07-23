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


# -- TaskBranchCommitter (finding 2) -----------------------------------------

class FakeGit:
    def __init__(self, current_branch="main", branch_exists=False,
                 fetch_ok=True):
        self.calls = []
        self.current_branch = current_branch
        self.branch_exists = branch_exists
        self.fetch_ok = fetch_ok

    def __call__(self, argv):
        self.calls.append(argv)
        joined = " ".join(argv)
        if "rev-parse --abbrev-ref HEAD" in joined:
            return 0, self.current_branch + "\n", ""
        if "rev-parse --verify" in joined:
            return (0, "", "") if self.branch_exists else (1, "", "")
        if argv[3] == "fetch":
            return (0, "", "") if self.fetch_ok else (1, "", "no network")
        return 0, "", ""


def _commit(tmp_path, fake):
    c = dp.TaskBranchCommitter(tmp_path, "dispatch/TASK-9", runner=fake)
    p = tmp_path / "state.yaml"
    p.write_text("x")
    c.commit([p], "msg")
    return ["\x00".join(call) for call in fake.calls]


def test_new_branch_based_on_origin_main_then_pushed(tmp_path):
    flat = _commit(tmp_path, FakeGit(current_branch="main"))
    assert any("fetch\x00origin\x00main" in f for f in flat)
    assert any("switch\x00-c\x00dispatch/TASK-9\x00origin/main" in f for f in flat)
    assert any("push\x00-u\x00origin\x00dispatch/TASK-9" in f for f in flat)


def test_existing_branch_switched_not_recreated(tmp_path):
    flat = _commit(tmp_path, FakeGit(current_branch="main", branch_exists=True))
    assert any(f.endswith("switch\x00dispatch/TASK-9") for f in flat)
    assert not any("switch\x00-c" in f for f in flat)


def test_already_on_branch_no_switch(tmp_path):
    flat = _commit(tmp_path, FakeGit(current_branch="dispatch/TASK-9"))
    assert not any("switch" in f for f in flat)
    assert any("commit" in f for f in flat)


def test_fetch_failure_falls_back_to_local_main_loudly(tmp_path, capsys):
    flat = _commit(tmp_path, FakeGit(current_branch="main", fetch_ok=False))
    assert any("switch\x00-c\x00dispatch/TASK-9\x00main" in f for f in flat)
    assert "WARN dispatch-branch" in capsys.readouterr().out


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
