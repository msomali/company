import json
from pathlib import Path

import pytest
import yaml

import dispatcher as dp
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
    "inputs": [{"artifact_id": "projects/PROJECT-000/charter.md"}],
    "budgets": {
        "wall_clock_minutes": 30,
        "tool_call_limit": 25,
        "model_budget_tag": "task:dry-run",
    },
}


class FakeBackend:
    def __init__(self):
        self.spawned = []

    def spawn(self, agent_id, prompt):
        self.spawned.append((agent_id, prompt))
        return f"run-{len(self.spawned):03d}"


class FakeCommitter:
    def __init__(self):
        self.commits = []

    def commit(self, paths, message):
        self.commits.append((list(paths), message))


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Repo skeleton + one created task + dispatcher with fakes."""
    (tmp_path / "control/schemas").mkdir(parents=True)
    for name in ("task.json", "state.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text()
        )
    (tmp_path / "control/manifests").mkdir()
    for code in ("sde", "sat", "pjm"):
        src = yaml.safe_load((REPO / f"control/manifests/{code}.yaml").read_text())
        (tmp_path / f"control/manifests/{code}.yaml").write_text(yaml.safe_dump(src))
    (tmp_path / "company").mkdir()
    (tmp_path / "company/digest-v1.1.md").write_text(
        (REPO / "company/digest-v1.1.md").read_text()
    )
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)

    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")
    env_file = tmp_path / "envelope.yaml"
    env_file.write_text(yaml.safe_dump(ENVELOPE))
    task_id = tc.create(env_file)

    d = dp.Dispatcher(
        repo_root=tmp_path, backend=FakeBackend(), committer=FakeCommitter()
    )
    return tmp_path, d, task_id


def task_dir_of(world_tuple):
    root, d, task_id = world_tuple
    return d.task_dir("PROJECT-000", task_id)


# ---------------------------------------------------------------- state machine

def test_forward_transitions_legal():
    assert "DISCOVERY" in dp.legal_transitions("INTAKE")
    assert "REQUIREMENTS" in dp.legal_transitions("DISCOVERY")
    assert "CLOSED" in dp.legal_transitions("OPERATIONS_AND_FEEDBACK")


def test_skipping_states_illegal():
    assert "IMPLEMENTATION" not in dp.legal_transitions("INTAKE")
    assert "DEPLOYMENT" not in dp.legal_transitions("DESIGN")


def test_review_loops_through_remediation():
    assert "REMEDIATION" in dp.legal_transitions("QUALITY_REVIEW")
    assert dp.legal_transitions("REMEDIATION") >= dp.REVIEW_STATES


def test_closed_is_terminal():
    assert dp.legal_transitions("CLOSED") == set()


def test_transition_updates_state_history_log_commit(world):
    root, d, task_id = world
    td = task_dir_of(world)
    d.transition(td, "DISCOVERY", evidence="PR #99")
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "DISCOVERY"
    assert state["history"][-1]["evidence"] == "PR #99"
    log = [json.loads(l) for l in (td / "log.jsonl").read_text().splitlines()]
    assert log[-1]["event"] == "transition"
    assert d.committer.commits, "transition must commit"
    assert "INTAKE → DISCOVERY" in d.committer.commits[-1][1]


def test_illegal_transition_raises_and_writes_nothing(world):
    root, d, task_id = world
    td = task_dir_of(world)
    with pytest.raises(dp.DispatchError):
        d.transition(td, "DEPLOYMENT", evidence="nope")
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "INTAKE"
    assert not d.committer.commits


def test_empty_evidence_rejected(world):
    root, d, task_id = world
    with pytest.raises(dp.DispatchError):
        d.transition(task_dir_of(world), "DISCOVERY", evidence="  ")


def test_blocked_resumes_only_to_preblock_state(world):
    root, d, task_id = world
    td = task_dir_of(world)
    d.transition(td, "DISCOVERY", evidence="e1")
    d.transition(td, "BLOCKED", evidence="ESC-x")
    with pytest.raises(dp.DispatchError):
        d.transition(td, "IMPLEMENTATION", evidence="resume-wrong")
    d.transition(td, "DISCOVERY", evidence="resumed after ESC")
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "DISCOVERY"


# -------------------------------------------------------------------- dispatch

def test_dispatch_refused_while_contract_only(world):
    """BA-2.4: manifests are contract-only during bootstrap; the dispatcher
    must refuse to spawn."""
    root, d, task_id = world
    with pytest.raises(dp.DispatchError) as exc:
        d.dispatch("PROJECT-000", task_id)
    assert "not 'active'" in str(exc.value)
    assert d.backend.spawned == []


def test_dispatch_happy_path_when_active(world):
    root, d, task_id = world
    mpath = root / "control/manifests/sde.yaml"
    m = yaml.safe_load(mpath.read_text())
    m["status"] = "active"  # simulating post-§88 human activation
    mpath.write_text(yaml.safe_dump(m))
    run_id = d.dispatch("PROJECT-000", task_id)
    assert run_id == "run-001"
    td = task_dir_of(world)
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["run_id"] == "run-001"
    assert state["iteration_count"] == 1
    agent_id, prompt = d.backend.spawned[0]
    assert agent_id == "sde"
    assert "## Task envelope" in prompt
    assert "projects/PROJECT-000/charter.md" in prompt  # artifact link
    # T1 → digest by reference, not inline
    assert "company/digest-v1.1.md" in prompt
    assert "OPENCLAW COMPANY DIGEST" not in prompt


def test_t2_prompt_inlines_digest(world):
    root, d, task_id = world
    td = task_dir_of(world)
    task = yaml.safe_load((td / "task.yaml").read_text())
    task["tier"] = "T2"
    prompt = d.build_prompt(task)
    assert "OPENCLAW COMPANY DIGEST" in prompt


def test_dispatch_missing_manifest(world):
    root, d, task_id = world
    td = task_dir_of(world)
    task = yaml.safe_load((td / "task.yaml").read_text())
    task["assigned_role"] = "DE"  # not copied into this world
    (td / "task.yaml").write_text(yaml.safe_dump(task))
    with pytest.raises(dp.DispatchError) as exc:
        d.dispatch("PROJECT-000", task_id)
    assert "no manifest" in str(exc.value)


def test_no_backend_means_no_dispatch(world):
    root, d, task_id = world
    d.backend = None
    with pytest.raises(dp.DispatchError) as exc:
        d.dispatch("PROJECT-000", task_id)
    assert "test-only" in str(exc.value)


# ------------------------------------------------------------ retry & caps

@pytest.mark.parametrize("cls,seq", [
    ("transient_infra", [(True, 30), (True, 120), (False, 0)]),
    ("rate_limit", [(True, 60), (True, 300), (False, 0)]),
    ("tool_timeout", [(True, 30), (False, 0)]),
    ("format_failure", [(True, 0), (False, 0)]),
    ("invalid_input", [(False, 0)]),
    ("policy_denial", [(False, 0)]),
    ("verification_failure", [(False, 0)]),
])
def test_retry_classes(cls, seq):
    for attempt, expected in enumerate(seq):
        assert dp.retry_decision(cls, attempt) == expected


def test_unknown_failure_class_raises():
    with pytest.raises(dp.DispatchError):
        dp.retry_decision("cosmic_rays", 0)


def test_tier_caps():
    assert dp.effective_caps({"tier": "T1", "budgets": {}}) == (30, 25)
    assert dp.effective_caps({"tier": "T2", "budgets": {}}) == (120, 100)
    t3 = {"tier": "T3",
          "budgets": {"wall_clock_minutes": 240, "tool_call_limit": 500}}
    assert dp.effective_caps(t3) == (240, 500)


# ------------------------------------------------------- loops & escalation

def test_loop_detection_identical_action_x3(world):
    root, d, task_id = world
    td = task_dir_of(world)
    assert d.check_loops(td) is None
    for _ in range(3):
        d.log(td, "action", fingerprint="edit:src/hello.md:same-diff")
    assert d.check_loops(td) == "identical action ×3"


def test_loop_detection_rejection_cycles(world):
    root, d, task_id = world
    td = task_dir_of(world)
    state = yaml.safe_load((td / "state.yaml").read_text())
    state["rejection_cycles"] = 2
    (td / "state.yaml").write_text(yaml.safe_dump(state, sort_keys=False))
    assert d.check_loops(td) == "rejection cycles ≥ 2"


def test_block_with_escalation_writes_esc_and_blocks(world):
    root, d, task_id = world
    td = task_dir_of(world)
    esc = d.block_with_escalation(td, "identical action ×3")
    assert esc.exists()
    text = esc.read_text()
    assert "type: escalation" in text and "§82.3" in text
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "BLOCKED"
    assert state["history"][-1]["evidence"] == esc.name


# ------------------------------------------------------- onboarded rule §82.7

def _advance_to_deployment(d, td):
    for s in ["DISCOVERY", "REQUIREMENTS", "DESIGN", "DELIVERY_PLAN",
              "IMPLEMENTATION", "QUALITY_REVIEW", "SECURITY_REVIEW",
              "PRIVACY_COMPLIANCE_REVIEW", "PRODUCTION_READINESS",
              "PRODUCT_ACCEPTANCE", "HUMAN_RELEASE_AUTHORIZATION"]:
        d.transition(td, s, evidence=f"advance:{s}")


def test_onboarded_charter_forces_t3_at_deployment(world):
    root, d, task_id = world
    charter = root / "projects/PROJECT-000/charter.md"
    charter.write_text(
        "---\norigin:\n  type: onboarded\n---\n# Charter\n"
    )
    td = task_dir_of(world)
    _advance_to_deployment(d, td)
    d.transition(td, "DEPLOYMENT", evidence="release approved")
    task = yaml.safe_load((td / "task.yaml").read_text())
    assert task["tier"] == "T3"
    log = [json.loads(l) for l in (td / "log.jsonl").read_text().splitlines()]
    assert any(r["event"] == "tier_forced" for r in log)


def test_native_charter_keeps_tier(world):
    root, d, task_id = world
    charter = root / "projects/PROJECT-000/charter.md"
    charter.write_text("---\norigin:\n  type: native\n---\n# Charter\n")
    td = task_dir_of(world)
    _advance_to_deployment(d, td)
    d.transition(td, "DEPLOYMENT", evidence="release approved")
    task = yaml.safe_load((td / "task.yaml").read_text())
    assert task["tier"] == "T1"
