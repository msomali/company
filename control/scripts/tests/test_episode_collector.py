import datetime
import json
from pathlib import Path

import pytest
import yaml

import episode_collector as ec
import task_create as tc

REPO = Path(__file__).resolve().parents[3]

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
    for name in ("task.json", "state.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text())
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)
    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")
    env = tmp_path / "e.yaml"
    env.write_text(yaml.safe_dump(ENVELOPE))
    task_id = tc.create(env)
    td = tmp_path / "projects/PROJECT-000/episodes" / task_id
    return tmp_path, task_id, td


def test_collect_writes_manifest_with_hashes_and_checklist(world):
    root, task_id, td = world
    manifest, problems = ec.collect(td)
    assert problems == []
    m = yaml.safe_load((td / "manifest.yaml").read_text())
    assert m["task_id"] == task_id
    assert set(m["files"]) == {"task.yaml", "state.yaml"}
    assert all(len(h) == 64 for h in m["files"].values())
    checks = m["completeness"]["checks"]
    assert checks["task_envelope"] and checks["state_transitions"]
    # no model calls yet → cost/transcript checks pass vacuously
    assert m["completeness"]["complete"] is True


def test_references_harvested_from_history_and_log(world):
    root, task_id, td = world
    state = yaml.safe_load((td / "state.yaml").read_text())
    state["history"].append({"at": "x", "from": "INTAKE", "to": "DISCOVERY",
                             "evidence": "PR #12 review"})
    (td / "state.yaml").write_text(yaml.safe_dump(state, sort_keys=False))
    with (td / "log.jsonl").open("a") as fh:
        fh.write(json.dumps({
            "at": "x", "event": "ci",
            "url": "https://github.com/msomali/company/actions/runs/123456",
        }) + "\n")
        fh.write(json.dumps({"at": "x", "event": "note",
                             "text": "see pull/14 for context"}) + "\n")
    manifest, _ = ec.collect(td)
    assert manifest["references"]["pull_requests"] == [12, 14]
    assert manifest["references"]["ci_runs"] == [
        "https://github.com/msomali/company/actions/runs/123456"]


def test_gate_records_included(world):
    root, task_id, td = world
    gates = root / "projects/PROJECT-000/gates"
    gates.mkdir()
    (gates / f"GATE-{task_id}-SAT-1.yaml").write_text("gate_id: x\n")
    (gates / "GATE-TASK-999-SAT-1.yaml").write_text("gate_id: y\n")
    manifest, _ = ec.collect(td)
    assert manifest["gate_records"] == [f"gates/GATE-{task_id}-SAT-1.yaml"]


def test_model_calls_require_usage_and_transcripts(world):
    root, task_id, td = world
    with (td / "log.jsonl").open("a") as fh:
        fh.write(json.dumps({"at": "x", "event": "model_usage",
                             "model": "m", "input_tokens": 1,
                             "output_tokens": 1,
                             "estimated_cost_usd": 0.0}) + "\n")
    manifest, _ = ec.collect(td)
    checks = manifest["completeness"]["checks"]
    assert checks["cost_tokens"] is False        # no usage.yaml
    assert checks["transcripts"] is False        # no transcripts/
    assert manifest["completeness"]["complete"] is False
    # add both → complete
    (td / "usage.yaml").write_text("total_estimated_cost_usd: 0.0\n")
    (td / "transcripts").mkdir()
    (td / "transcripts/session-1.json").write_text("{}")
    manifest, _ = ec.collect(td)
    assert manifest["completeness"]["complete"] is True


def test_check_mode_detects_drift(world):
    root, task_id, td = world
    ec.collect(td)
    _, problems = ec.collect(td, check=True)
    assert problems == []
    (td / "task.yaml").write_text((td / "task.yaml").read_text() + "# edited\n")
    _, problems = ec.collect(td, check=True)
    assert any("content changed" in p for p in problems)
    (td / "extra.txt").write_text("late file")
    _, problems = ec.collect(td, check=True)
    assert any("new file" in p for p in problems)


def test_collector_never_mutates_inputs(world):
    root, task_id, td = world
    before = {p: p.read_bytes() for p in td.rglob("*") if p.is_file()}
    ec.collect(td)
    after = {p: p.read_bytes() for p in td.rglob("*")
             if p.is_file() and p.name != "manifest.yaml"}
    assert before == after


def test_missing_required_file_fails(world):
    root, task_id, td = world
    (td / "state.yaml").unlink()
    with pytest.raises(ec.CollectorError, match="state.yaml"):
        ec.collect(td)


def test_cli_exit_codes(world, capsys):
    # filesystem-only fixture (no git tree) opts out of ref verification;
    # the tracked-on-a-ref path is covered against real git in test_task_lane.
    root, task_id, td = world
    assert ec.main([str(td), "--no-verify-refs"]) == 0
    out = capsys.readouterr().out
    assert "complete" in out


def test_cli_verify_refs_default_errors_outside_git_tree(world, capsys):
    root, task_id, td = world
    assert ec.main([str(td)]) == 1                 # verify-refs on by default
    assert "not inside a git tree" in capsys.readouterr().out


# -- ADR-B007 bound requirement: --check verifies attested gate records -------
# -- still exist in THIS tree (the lane once PR 2 wires the caller) -----------

def _seed_gate(root, task_id, gate):
    gates = root / "projects/PROJECT-000/gates"
    gates.mkdir(parents=True, exist_ok=True)
    p = gates / f"GATE-{task_id}-{gate}-1.yaml"
    p.write_text(yaml.safe_dump({"gate_id": f"GATE-{task_id}-{gate}-1",
                                 "gate_owner": gate, "decision": "APPROVED"}))
    return p


def test_manifest_lists_gate_records_present_in_this_tree(world):
    root, task_id, td = world
    _seed_gate(root, task_id, "SAT")
    _seed_gate(root, task_id, "HUMAN")
    manifest, _ = ec.collect(td)
    assert manifest["gate_records"] == [
        f"gates/GATE-{task_id}-HUMAN-1.yaml",
        f"gates/GATE-{task_id}-SAT-1.yaml",
    ]


def test_check_fails_when_attested_gate_record_vanishes(world):
    root, task_id, td = world
    sat = _seed_gate(root, task_id, "SAT")
    ec.collect(td)                                   # manifest attests to SAT
    sat.unlink()                                     # record leaves this tree
    _, problems = ec.collect(td, check=True)
    assert any("gate record vanished from the lane" in p for p in problems)
    assert any(f"GATE-{task_id}-SAT-1.yaml" in p for p in problems)


def test_check_passes_when_attested_gate_records_present(world):
    root, task_id, td = world
    _seed_gate(root, task_id, "SAT")
    ec.collect(td)
    _, problems = ec.collect(td, check=True)
    assert problems == []
