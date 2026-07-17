import copy
from pathlib import Path

import pytest
import yaml

import task_create as tc

REPO = Path(__file__).resolve().parents[3]

VALID = {
    "project_id": "PROJECT-000",
    "requested_by": "PJM",
    "assigned_role": "SDE",
    "objective": "Implement the dry-run hello artifact per charter.",
    "business_context": "PROJECT-000 dry run",
    "inputs": [{"artifact_id": "projects/PROJECT-000/charter.md"}],
    "constraints": ["no production access"],
    "risk_class": "low",
    "tier": "T1",
    "data_classification": "internal",
    "acceptance_criteria": ["artifact exists and passes CI"],
    "required_outputs": ["projects/PROJECT-000/src/hello.md"],
    "priority": "medium",
    "allowed_tools": "inherited-and-narrowed",
    "budgets": {
        "wall_clock_minutes": 30,
        "tool_call_limit": 25,
        "model_budget_tag": "task:dry-run",
        "retries": 1,
    },
}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    (tmp_path / "control/schemas").mkdir(parents=True)
    for name in ("task.json", "state.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text()
        )
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)
    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")
    return tmp_path


def envelope_file(root: Path, data: dict) -> Path:
    p = root / "envelope.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


def test_valid_envelope_creates_task_and_state(sandbox):
    task_id = tc.create(envelope_file(sandbox, VALID))
    assert task_id == "TASK-001"
    task_dir = sandbox / "projects/PROJECT-000/episodes/TASK-001"
    task = yaml.safe_load((task_dir / "task.yaml").read_text())
    state = yaml.safe_load((task_dir / "state.yaml").read_text())
    assert task["task_id"] == "TASK-001"
    assert task["objective"] == VALID["objective"]
    assert state["state"] == "INTAKE"
    assert state["history"][0]["to"] == "INTAKE"


def test_sequential_allocation(sandbox):
    assert tc.create(envelope_file(sandbox, VALID)) == "TASK-001"
    assert tc.create(envelope_file(sandbox, VALID)) == "TASK-002"
    # gaps do not confuse allocation
    (sandbox / "projects/PROJECT-000/episodes/TASK-041").mkdir()
    assert tc.create(envelope_file(sandbox, VALID)) == "TASK-042"


@pytest.mark.parametrize("missing", [
    "objective", "acceptance_criteria", "assigned_role", "risk_class",
    "tier", "required_outputs", "budgets", "priority", "data_classification",
])
def test_missing_mandatory_field_rejected(sandbox, missing):
    bad = copy.deepcopy(VALID)
    del bad[missing]
    with pytest.raises(tc.Rejection) as exc:
        tc.create(envelope_file(sandbox, bad))
    assert missing in str(exc.value)
    assert not (sandbox / "projects/PROJECT-000/episodes").exists()


def test_rejection_lists_all_failures_not_just_first(sandbox):
    bad = copy.deepcopy(VALID)
    del bad["objective"]
    del bad["tier"]
    bad["risk_class"] = "prohibited"
    with pytest.raises(tc.Rejection) as exc:
        tc.create(envelope_file(sandbox, bad))
    text = str(exc.value)
    assert "objective" in text and "tier" in text and "prohibited" in text


def test_supplied_task_id_rejected(sandbox):
    bad = dict(copy.deepcopy(VALID), task_id="TASK-999")
    with pytest.raises(tc.Rejection) as exc:
        tc.create(envelope_file(sandbox, bad))
    assert "task-create allocates it" in str(exc.value)


def test_unknown_project_rejected(sandbox):
    bad = dict(copy.deepcopy(VALID), project_id="PROJECT-999")
    with pytest.raises(tc.Rejection) as exc:
        tc.create(envelope_file(sandbox, bad))
    assert "no such project" in str(exc.value)


def test_self_assignment_rejected(sandbox):
    bad = dict(copy.deepcopy(VALID), requested_by="SDE")
    with pytest.raises(tc.Rejection) as exc:
        tc.create(envelope_file(sandbox, bad))
    assert "separation of duties" in str(exc.value)


def test_unknown_field_rejected_additional_properties(sandbox):
    bad = dict(copy.deepcopy(VALID), surprise="field")
    with pytest.raises(tc.Rejection):
        tc.create(envelope_file(sandbox, bad))


def test_budget_bounds(sandbox):
    bad = copy.deepcopy(VALID)
    bad["budgets"]["retries"] = 3  # schema max 2 (§82.3 retry ceiling)
    with pytest.raises(tc.Rejection):
        tc.create(envelope_file(sandbox, bad))
    bad2 = copy.deepcopy(VALID)
    bad2["budgets"]["wall_clock_minutes"] = 0
    with pytest.raises(tc.Rejection):
        tc.create(envelope_file(sandbox, bad2))


def test_rejection_writes_nothing(sandbox):
    bad = copy.deepcopy(VALID)
    del bad["objective"]
    bad_file = envelope_file(sandbox, bad)
    before = {p for p in sandbox.rglob("*")}
    with pytest.raises(tc.Rejection):
        tc.create(bad_file)
    after = {p for p in sandbox.rglob("*")}
    assert before == after


def test_validate_only_mode(sandbox):
    assert tc.create(envelope_file(sandbox, VALID), validate_only=True) == "VALID"
    assert not (sandbox / "projects/PROJECT-000/episodes").exists()


def test_no_model_client_imported():
    """§82.1: no model call occurs — structurally, the module must not import
    any model/HTTP client."""
    import sys
    banned = {"anthropic", "openai", "litellm", "requests", "httpx", "urllib3"}
    tc_modules = {m.split(".")[0] for m in sys.modules if not m.startswith("_")}
    assert not (banned & tc_modules & set(_imports_of(tc)))


def _imports_of(module):
    import ast
    tree = ast.parse(Path(module.__file__).read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_cli_exit_codes(sandbox, capsys):
    good = envelope_file(sandbox, VALID)
    assert tc.main([str(good)]) == 0
    assert "TASK-001" in capsys.readouterr().out
    bad = copy.deepcopy(VALID)
    del bad["objective"]
    bad_file = sandbox / "bad.yaml"
    bad_file.write_text(yaml.safe_dump(bad))
    assert tc.main([str(bad_file)]) == 2
    out = capsys.readouterr().out
    assert "REJECTED" in out and "objective" in out
