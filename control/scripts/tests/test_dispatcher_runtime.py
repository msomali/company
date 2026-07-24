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
    monkeypatch.setattr(dp, "TaskBranchCommitter",
                        lambda *a, **k: NullCommitter())
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


# -- dispatch-once (activation item 1, 2026-07-21) ---------------------------


class FakeSpawnBackend:
    """Test double for the one-shot path; mirrors OpenClawSessionBackend's
    constructor surface and spawn contract."""

    def __init__(self, policies_path=None, timeout_seconds=None):
        self.policies_path = policies_path
        self.timeout_seconds = timeout_seconds
        self.spawned = []
        self.last_response = {"meta": {"durationMs": 42}}

    def spawn(self, agent_id, prompt):
        self.spawned.append((agent_id, prompt))
        return f"agent:{agent_id}:fake-run"


def _activate_sde(root):
    (root / "control/manifests").mkdir(parents=True, exist_ok=True)
    (root / "control/manifests/sde.yaml").write_text(
        yaml.safe_dump({"role": "SDE", "status": "active"}))


def test_dispatch_once_dry_run_refuses_loudly_and_spawns_nothing(
        world, capsys, monkeypatch):
    root, task_id = world
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)

    def exploding_factory(**kw):
        raise AssertionError("dry-run must never construct a backend")

    code = rt.dispatch_once(root, "PROJECT-000", task_id, live=False,
                            backend_factory=exploding_factory)
    assert code == 2
    out = capsys.readouterr().out
    assert "WOULD REFUSE" in out
    assert "no manifest for role SDE" in out
    assert "OPENCLAW_GATEWAY_TOKEN missing" in out
    assert "nothing spawned" in out
    state = yaml.safe_load(
        (root / f"projects/PROJECT-000/episodes/{task_id}/state.yaml").read_text())
    assert state["run_id"] is None  # dry-run is read-only


def test_dispatch_once_dry_run_clean_exits_zero(world, capsys, monkeypatch):
    root, task_id = world
    _activate_sde(root)
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "t0k")
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", "/etc/company/openclaw-dispatcher.json")
    code = rt.dispatch_once(root, "PROJECT-000", task_id, live=False)
    assert code == 0
    out = capsys.readouterr().out
    assert "WOULD REFUSE" not in out
    assert "--timeout: 1800s" in out          # 30-min envelope budget → seconds
    assert "token present: yes" in out
    assert "t0k" not in out                   # value never printed
    assert "--session-key agent:sde:" in out
    # seat-config surfacing (first-live-spawn failure 2026-07-21): the CLI
    # resolves --agent from the INVOKING user's config — the dry-run must
    # show which config the seat would use
    assert "OPENCLAW_CONFIG_PATH=/etc/company/openclaw-dispatcher.json" in out


def test_dispatch_once_dry_run_warns_when_seat_config_unset(
        world, capsys, monkeypatch):
    root, task_id = world
    _activate_sde(root)
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "t0k")
    monkeypatch.delenv("OPENCLAW_CONFIG_PATH", raising=False)
    rt.dispatch_once(root, "PROJECT-000", task_id, live=False)
    out = capsys.readouterr().out
    assert "OPENCLAW_CONFIG_PATH=(unset" in out
    assert "seat-check" in out


def test_dispatch_once_live_spawns_records_and_reports(
        world, capsys, monkeypatch):
    root, task_id = world
    _activate_sde(root)
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "t0k")

    class NullCommitter:
        def commit(self, paths, message):
            pass

    import dispatcher as dp
    monkeypatch.setattr(dp, "GitCommitter", lambda root_: NullCommitter())
    monkeypatch.setattr(dp, "TaskBranchCommitter",
                        lambda *a, **k: NullCommitter())
    made = []

    def factory(**kw):
        b = FakeSpawnBackend(**kw)
        made.append(b)
        return b

    code = rt.dispatch_once(root, "PROJECT-000", task_id, live=True,
                            backend_factory=factory)
    assert code == 0
    assert made[0].timeout_seconds == 1800
    agent_id, prompt = made[0].spawned[0]
    assert agent_id == "sde"
    assert "Task envelope" in prompt
    out = capsys.readouterr().out
    assert "spawned agent:sde:fake-run" in out
    state = yaml.safe_load(
        (root / f"projects/PROJECT-000/episodes/{task_id}/state.yaml").read_text())
    assert state["run_id"] == "agent:sde:fake-run"


def test_dispatch_once_live_refused_without_manifest_never_builds_backend(
        world, capsys, monkeypatch):
    root, task_id = world
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "t0k")

    def exploding_factory(**kw):
        raise AssertionError("refused live run must never construct a backend")

    code = rt.dispatch_once(root, "PROJECT-000", task_id, live=True,
                            backend_factory=exploding_factory)
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_dispatch_once_cli_requires_project_and_task(world):
    root, _ = world
    with pytest.raises(SystemExit):
        rt.main(["--dispatch-once", "--repo-root", str(root)])


# -- --transition: owner-invoked §82.4 walk (delivery-cycle item 7) ----------

class _NullCommitter:
    def commit(self, paths, message):
        pass


def _null_committers(monkeypatch):
    import dispatcher as dp
    monkeypatch.setattr(dp, "GitCommitter", lambda root_: _NullCommitter())
    monkeypatch.setattr(dp, "TaskBranchCommitter",
                        lambda *a, **k: _NullCommitter())


def test_transition_walks_forward_edge(world, capsys, monkeypatch):
    root, task_id = world
    _null_committers(monkeypatch)
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", task_id,
                    "--to", "DISCOVERY", "--evidence", "PR #112 merged"])
    assert code == 0
    assert f"{task_id} → DISCOVERY" in capsys.readouterr().out
    td = root / "projects/PROJECT-000/episodes" / task_id
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "DISCOVERY"
    assert state["history"][-1]["evidence"] == "PR #112 merged"
    log = (td / "log.jsonl").read_text()
    assert '"transition"' in log


def test_transition_illegal_edge_refused(world, capsys, monkeypatch):
    root, task_id = world
    _null_committers(monkeypatch)
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", task_id,
                    "--to", "CLOSED", "--evidence", "nope"])
    assert code == 2
    assert "REFUSED" in capsys.readouterr().out
    td = root / "projects/PROJECT-000/episodes" / task_id
    assert yaml.safe_load((td / "state.yaml").read_text())["state"] == "INTAKE"


def test_transition_blank_evidence_refused(world, capsys, monkeypatch):
    root, task_id = world
    _null_committers(monkeypatch)
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", task_id,
                    "--to", "DISCOVERY", "--evidence", "  "])
    assert code == 2
    assert "evidence" in capsys.readouterr().out


def test_transition_unknown_task_refused(world, capsys, monkeypatch):
    root, _ = world
    _null_committers(monkeypatch)
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", "TASK-404",
                    "--to", "DISCOVERY", "--evidence", "x"])
    assert code == 2
    assert "no such task" in capsys.readouterr().out


# -- gate interlock (owner ruling 2026-07-23): records structurally
# -- unskippable --------------------------------------------------------------

def _force_state(root, task_id, state_name):
    td = root / "projects/PROJECT-000/episodes" / task_id
    s = yaml.safe_load((td / "state.yaml").read_text())
    s["state"] = state_name
    s["history"].append({"at": "2026-07-23T00:00:00Z", "from": "SETUP",
                         "to": state_name, "evidence": "test setup"})
    (td / "state.yaml").write_text(yaml.safe_dump(s, sort_keys=False))
    return td


def test_transition_refuses_every_gate_owned_exit(world, capsys, monkeypatch):
    """All six gate states: the approve-target exit refuses and the message
    names the owning gate + --process-review. Derived from the SAME
    approvals table the runtime uses — a new gate is guarded by import."""
    import approvals as ap
    root, task_id = world
    _null_committers(monkeypatch)
    for gate, (expected, advance_to) in ap.GATE_TRANSITIONS.items():
        td = _force_state(root, task_id, expected)
        code = rt.main(["--transition", "--repo-root", str(root),
                        "--project", "PROJECT-000", "--task", task_id,
                        "--to", advance_to, "--evidence", "bypass attempt"])
        out = capsys.readouterr().out
        assert code == 2, (gate, out)
        assert "gate-owned" in out and gate in out
        assert "--process-review" in out
        state = yaml.safe_load((td / "state.yaml").read_text())
        assert state["state"] == expected          # untouched


def test_transition_refuses_remediation_exit_from_review(world, capsys,
                                                         monkeypatch):
    """The REJECT target is gate work too — a recordless walk to
    REMEDIATION would skip the gate record AND the rejection counter."""
    root, task_id = world
    _null_committers(monkeypatch)
    _force_state(root, task_id, "QUALITY_REVIEW")
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", task_id,
                    "--to", "REMEDIATION", "--evidence", "recordless reject"])
    assert code == 2
    out = capsys.readouterr().out
    assert "SAT" in out and "--process-review" in out


def test_transition_blocked_exit_from_gate_state_allowed(world, capsys,
                                                         monkeypatch):
    """Escalation is not a gate decision: BLOCKED stays reachable."""
    root, task_id = world
    _null_committers(monkeypatch)
    td = _force_state(root, task_id, "QUALITY_REVIEW")
    code = rt.main(["--transition", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--task", task_id,
                    "--to", "BLOCKED", "--evidence", "ESC-manual: stuck"])
    assert code == 0
    assert yaml.safe_load((td / "state.yaml").read_text())["state"] == "BLOCKED"


def test_process_review_still_walks_gate_edges(world, capsys, monkeypatch):
    """The interlock lives in --transition only: the approvals path (which
    writes the record) still transitions gate states normally."""
    root, task_id = world
    _null_committers(monkeypatch)
    _force_state(root, task_id, "QUALITY_REVIEW")
    monkeypatch.setattr("sys.stdin",
                        __import__("io").StringIO(f"APPROVE {task_id} SAT — ok\n"))
    code = rt.main(["--process-review", "--repo-root", str(root),
                    "--project", "PROJECT-000", "--approver", "msomali",
                    "--reference", "PR#interlock-test"])
    assert code == 0
    td = root / "projects/PROJECT-000/episodes" / task_id
    assert yaml.safe_load((td / "state.yaml").read_text())["state"] == \
        "SECURITY_REVIEW"


# -- scan union: lane-authoritative + divergence WARN (ADR-B007 PR 2) --------

def _lane_state(lanes_root, task_id, state, project="PROJECT-000"):
    sf = (lanes_root / task_id / "projects" / project / "episodes" / task_id
          / "state.yaml")
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(yaml.safe_dump(
        {"task_id": task_id, "state": state, "run_id": None,
         "rejection_cycles": 0}))


def test_scan_reports_union_lane_authoritative(world, tmp_path):
    root, task_id = world               # task_id lives in the clone at INTAKE
    lanes = tmp_path / "lanes"
    _lane_state(lanes, task_id, "IMPLEMENTATION")   # same task, advanced lane
    _lane_state(lanes, "TASK-090", "DISCOVERY")     # lane-only task
    rows, warnings = rt.scan(root, lanes)
    by = {r["task"]: r for r in rows}
    assert by[task_id]["state"] == "IMPLEMENTATION"   # lane wins
    assert by[task_id]["source"] == "lane"
    assert by["TASK-090"]["source"] == "lane"
    # divergence (clone INTAKE vs lane IMPLEMENTATION) is a loud WARN
    assert any(task_id in w and "diverges" in w for w in warnings)


def test_scan_clone_only_when_no_lane(world, tmp_path):
    root, task_id = world
    rows, warnings = rt.scan(root, tmp_path / "empty-lanes")
    assert [r["source"] for r in rows] == ["main"]
    assert warnings == []


def test_once_prints_divergence_warning(world, tmp_path, capsys):
    root, task_id = world
    lanes = tmp_path / "lanes"
    _lane_state(lanes, task_id, "DESIGN")
    assert rt.main(["--once", "--repo-root", str(root),
                    "--lanes-root", str(lanes)]) == 0
    out = capsys.readouterr().out
    assert "WARN scan-divergence" in out
    assert f"{task_id}: DESIGN" in out and "[lane]" in out
