import datetime
from pathlib import Path

import pytest
import yaml

import dispatcher_runtime as rt
import task_create as tc

REPO = Path(__file__).resolve().parents[3]

REGISTER = "| Named owner | msomali (GitHub: @msomali) |\n"

ENVELOPE = {
    "project_id": "PROJECT-000",
    "requested_by": "PJM",
    "assigned_role": "SDE",
    "objective": "Implement the dry-run hello artifact per charter.",
    "risk_class": "low",
    "tier": "T1",
    "data_classification": "internal",
    "acceptance_criteria": ["artifact exists"],
    "required_outputs": ["projects/PROJECT-000/src/hello.md"],
    "priority": "medium",
    "budgets": {"wall_clock_minutes": 30, "tool_call_limit": 25,
                "model_budget_tag": "task:dry-run"},
}


@pytest.fixture
def world(tmp_path, monkeypatch):
    (tmp_path / "control/schemas").mkdir(parents=True)
    for name in ("task.json", "state.json", "gate.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text())
    (tmp_path / "control/registers").mkdir()
    (tmp_path / "control/registers/s51.md").write_text(REGISTER)
    (tmp_path / "control/models").mkdir()
    (tmp_path / "control/models/policies.yaml").write_text(
        yaml.safe_dump({"mode_s": {"concurrency_cap": 3}}))
    (tmp_path / "control/models/prices.yaml").write_text(yaml.safe_dump({
        "as_of": datetime.date.today().isoformat(), "models": {}}))
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)
    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")
    env = tmp_path / "e.yaml"
    env.write_text(yaml.safe_dump(ENVELOPE))
    task_id = tc.create(env)
    return tmp_path, task_id


def test_once_reports_and_exits_zero(world, capsys, monkeypatch):
    root, task_id = world
    # commits during any transitions are not exercised here; --once is read-only
    assert rt.main(["--once", "--repo-root", str(root)]) == 0
    out = capsys.readouterr().out
    assert f"PROJECT-000/{task_id}: INTAKE" in out
    assert "concurrency cap=3" in out


def test_once_is_read_only(world):
    root, task_id = world
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    rt.main(["--once", "--repo-root", str(root)])
    after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_process_review_owner_applies(world, capsys, monkeypatch):
    root, task_id = world

    class NullCommitter:
        def commit(self, paths, message):
            pass

    import dispatcher as dp
    monkeypatch.setattr(dp, "GitCommitter", lambda root_: NullCommitter())
    # advance to QUALITY_REVIEW so a SAT decision is applicable
    d = dp.Dispatcher(repo_root=root, backend=None, committer=NullCommitter())
    td = d.task_dir("PROJECT-000", task_id)
    for s in ["DISCOVERY", "REQUIREMENTS", "DESIGN", "DELIVERY_PLAN",
              "IMPLEMENTATION", "QUALITY_REVIEW"]:
        d.transition(td, s, evidence=f"advance:{s}")

    monkeypatch.setattr("sys.stdin",
                        __import__("io").StringIO(f"APPROVE {task_id} SAT — ok\n"))
    code = rt.main(["--process-review", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--approver", "msomali",
                    "--reference", "PR#test"])
    assert code == 0
    out = capsys.readouterr().out
    assert f"applied: APPROVE {task_id} SAT" in out
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "SECURITY_REVIEW"


def test_process_review_bot_refused(world, capsys, monkeypatch):
    root, task_id = world

    class NullCommitter:
        def commit(self, paths, message):
            pass

    import dispatcher as dp
    monkeypatch.setattr(dp, "GitCommitter", lambda root_: NullCommitter())
    monkeypatch.setattr("sys.stdin",
                        __import__("io").StringIO(f"APPROVE {task_id} SAT\n"))
    code = rt.main(["--process-review", "--repo-root", str(root),
                    "--project", "PROJECT-000",
                    "--approver", "agenticfoundrybot",
                    "--reference", "PR#test"])
    assert code == 1
    assert "refused" in capsys.readouterr().out


def test_process_review_no_decisions_is_noop(world, capsys, monkeypatch):
    root, task_id = world

    class NullCommitter:
        def commit(self, paths, message):
            pass

    import dispatcher as dp
    monkeypatch.setattr(dp, "GitCommitter", lambda root_: NullCommitter())
    monkeypatch.setattr("sys.stdin",
                        __import__("io").StringIO("Looks good to me!\n"))
    code = rt.main(["--process-review", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--approver", "msomali",
                    "--reference", "PR#test"])
    assert code == 0
    assert "no inference" in capsys.readouterr().out
