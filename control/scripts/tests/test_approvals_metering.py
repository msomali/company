import datetime
from pathlib import Path

import pytest
import yaml

import approvals as ap
import dispatcher as dp
import metering as mt
import task_create as tc

REPO = Path(__file__).resolve().parents[3]

REGISTER = """# Owner Record (v1 §51)
| Named owner | msomali (GitHub: @msomali) |
"""

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
    "budgets": {
        "wall_clock_minutes": 30,
        "tool_call_limit": 25,
        "model_budget_tag": "task:dry-run",
        "model_cost_limit_usd": 1.0,
    },
}


class FakeCommitter:
    def __init__(self):
        self.commits = []

    def commit(self, paths, message):
        self.commits.append((list(paths), message))


@pytest.fixture
def world(tmp_path, monkeypatch):
    (tmp_path / "control/schemas").mkdir(parents=True)
    for name in ("task.json", "state.json", "gate.json"):
        (tmp_path / "control/schemas" / name).write_text(
            (REPO / "control/schemas" / name).read_text()
        )
    (tmp_path / "control/registers").mkdir()
    (tmp_path / "control/registers/section-51.md").write_text(REGISTER)
    (tmp_path / "control/models").mkdir()
    (tmp_path / "control/models/prices.yaml").write_text(yaml.safe_dump({
        "as_of": datetime.date.today().isoformat(),
        "models": {"anthropic/claude-fable-5":
                   {"input_per_mtok": 10.0, "output_per_mtok": 50.0}},
    }))
    (tmp_path / "control/models/policies.yaml").write_text(yaml.safe_dump({
        "mode_s": {"concurrency_cap": 2},
    }))
    (tmp_path / "projects/PROJECT-000").mkdir(parents=True)

    monkeypatch.setattr(tc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tc, "TASK_SCHEMA", tmp_path / "control/schemas/task.json")
    monkeypatch.setattr(tc, "STATE_SCHEMA", tmp_path / "control/schemas/state.json")
    monkeypatch.setattr(tc, "PROJECTS_DIR", tmp_path / "projects")
    env = tmp_path / "e.yaml"
    env.write_text(yaml.safe_dump(ENVELOPE))
    task_id = tc.create(env)

    d = dp.Dispatcher(repo_root=tmp_path, backend=None, committer=FakeCommitter())
    cap = ap.ApprovalsCapture(d, repo_root=tmp_path)
    td = d.task_dir("PROJECT-000", task_id)
    return tmp_path, d, cap, task_id, td


def advance(d, td, *states):
    for s in states:
        d.transition(td, s, evidence=f"advance:{s}")


TO_QUALITY = ["DISCOVERY", "REQUIREMENTS", "DESIGN", "DELIVERY_PLAN",
              "IMPLEMENTATION", "QUALITY_REVIEW"]


# ------------------------------------------------------------------ identity

def test_owner_identity_parsed_from_register(world):
    root, d, cap, task_id, td = world
    assert cap.owner == "msomali"


def test_no_register_no_approvals(tmp_path):
    with pytest.raises(ap.ApprovalError, match="no §51 owner register"):
        ap.owner_identity(tmp_path)


def test_bot_review_never_satisfies_gate(world):
    root, d, cap, task_id, td = world
    decision = ap.Decision("APPROVE", task_id, "SAT",
                           approver="agenticfoundrybot", reference="PR#1")
    with pytest.raises(ap.ApprovalError, match="never"):
        cap.apply("PROJECT-000", decision)


def test_third_party_review_refused(world):
    root, d, cap, task_id, td = world
    decision = ap.Decision("APPROVE", task_id, "SAT",
                           approver="someone-else", reference="PR#1")
    with pytest.raises(ap.ApprovalError):
        cap.apply("PROJECT-000", decision)


# ------------------------------------------------------------------- parsing

def test_parse_wellformed_decisions():
    body = ("Looks good.\n"
            "APPROVE TASK-001 SAT — solid evidence\n"
            "REJECT TASK-002 SSE: needs threat model\n")
    ds = ap.parse_decisions(body, "msomali", "PR#7")
    assert [(d.verb, d.task_id, d.gate) for d in ds] == [
        ("APPROVE", "TASK-001", "SAT"), ("REJECT", "TASK-002", "SSE")]
    assert ds[0].note == "solid evidence"


def test_malformed_lines_ignored_never_inferred():
    body = ("approve TASK-001 SAT\n"        # lowercase verb — not a decision
            "APPROVE TASK-1 SAT\n"          # bad id
            "APPROVE TASK-001 QA\n"         # unknown gate
            "APPROVED TASK-001 SAT\n"       # wrong verb form
            "I would approve this if...\n")
    assert ap.parse_decisions(body, "msomali", "x") == []


# ------------------------------------------------------------ gate mechanics

def test_approve_advances_and_writes_gate_record(world):
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    decision = ap.Decision("APPROVE", task_id, "SAT",
                           approver="msomali", reference="PR#9-review-1")
    record_path = cap.apply("PROJECT-000", decision)
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "SECURITY_REVIEW"
    record = yaml.safe_load(record_path.read_text())
    assert record["gate_owner"] == "SAT"
    assert record["decision"] == "APPROVED"
    assert record["approval_message_ref"] == "PR#9-review-1"
    assert record_path.parent.name == "gates"


def test_wrong_state_refused_no_reordering(world):
    root, d, cap, task_id, td = world  # still INTAKE
    decision = ap.Decision("APPROVE", task_id, "SAT",
                           approver="msomali", reference="PR#9")
    with pytest.raises(ap.ApprovalError, match="requires state QUALITY_REVIEW"):
        cap.apply("PROJECT-000", decision)


def test_reject_goes_to_remediation_and_counts_cycle(world):
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    decision = ap.Decision("REJECT", task_id, "SAT",
                           approver="msomali", reference="PR#9")
    cap.apply("PROJECT-000", decision)
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "REMEDIATION"
    assert state["rejection_cycles"] == 1


def test_second_rejection_blocks_via_loop_detection(world):
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    cap.apply("PROJECT-000", ap.Decision("REJECT", task_id, "SAT",
                                         "msomali", "PR#9"))
    d.transition(td, "QUALITY_REVIEW", evidence="remediated")
    cap.apply("PROJECT-000", ap.Decision("REJECT", task_id, "SAT",
                                         "msomali", "PR#10"))
    state = yaml.safe_load((td / "state.yaml").read_text())
    assert state["state"] == "BLOCKED"
    assert state["rejection_cycles"] == 2
    assert any(p.name.startswith("ESC-") for p in td.iterdir())


def test_gate_records_immutable_but_cycles_sequence(world):
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    p1 = cap.apply("PROJECT-000", ap.Decision("REJECT", task_id, "SAT",
                                              "msomali", "PR#9"))
    assert p1.name == f"GATE-{task_id}-SAT-1.yaml"
    d.transition(td, "QUALITY_REVIEW", evidence="remediated")
    p2 = cap.apply("PROJECT-000", ap.Decision("APPROVE", task_id, "SAT",
                                              "msomali", "PR#10"))
    assert p2.name == f"GATE-{task_id}-SAT-2.yaml"
    assert p1.exists() and p2.exists()  # earlier record untouched
    # overwriting an existing record is refused
    record = cap._gate_record(td, ap.Decision("APPROVE", task_id, "SAT",
                                              "msomali", "PR#11"))
    record["gate_id"] = f"GATE-{task_id}-SAT-2"  # force collision
    with pytest.raises(ap.ApprovalError, match="immutable"):
        cap._write_record(td, ap.Decision("APPROVE", task_id, "SAT",
                                          "msomali", "PR#11"), record)


def test_overdue_stays_put_no_timeout_proceeds(world):
    """No code path advances state on time. Structural check: the approvals
    module never imports time/sleep-based scheduling and provides no
    timeout API."""
    import ast
    src = (REPO / "control/scripts/approvals.py").read_text()
    tree = ast.parse(src)
    imported = {n.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for n in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}
    assert "time" not in imported and "sched" not in imported
    assert "timeout" not in src.lower().replace("no timeout-proceeds", "")


# -------------------------------------------------------------------- meter

def test_cost_computation_and_running_totals(world):
    root, d, cap, task_id, td = world
    m = mt.Meter(prices_path=root / "control/models/prices.yaml")
    u1 = m.record_usage(td, model="anthropic/claude-fable-5",
                        input_tokens=100_000, output_tokens=10_000)
    assert u1["total_estimated_cost_usd"] == pytest.approx(1.5)
    u2 = m.record_usage(td, model="anthropic/claude-fable-5",
                        input_tokens=50_000, output_tokens=0)
    assert u2["calls"] == 2
    assert u2["total_estimated_cost_usd"] == pytest.approx(2.0)


def test_stale_prices_refused(world, tmp_path):
    root, *_ = world
    stale = tmp_path / "stale-prices.yaml"
    old = (datetime.date.today() - datetime.timedelta(days=91)).isoformat()
    stale.write_text(yaml.safe_dump({
        "as_of": old,
        "models": {"m": {"input_per_mtok": 1, "output_per_mtok": 1}},
    }))
    with pytest.raises(mt.MeteringError, match="days old"):
        mt.Meter(prices_path=stale)


def test_missing_as_of_refused(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text(yaml.safe_dump({"models": {}}))
    with pytest.raises(mt.MeteringError, match="as_of"):
        mt.Meter(prices_path=p)


def test_unknown_model_refused(world):
    root, d, cap, task_id, td = world
    m = mt.Meter(prices_path=root / "control/models/prices.yaml")
    with pytest.raises(mt.MeteringError, match="no rate"):
        m.cost_usd("openai/unlisted", 1, 1)


def test_ceiling_breach_raises_budget_exceeded(world):
    root, d, cap, task_id, td = world
    m = mt.Meter(prices_path=root / "control/models/prices.yaml")
    m.record_usage(td, model="anthropic/claude-fable-5",
                   input_tokens=100_000, output_tokens=0)  # 1.0 — at ceiling
    m.enforce_ceiling(td)  # exactly at ceiling: not a breach
    m.record_usage(td, model="anthropic/claude-fable-5",
                   input_tokens=1_000, output_tokens=0)
    with pytest.raises(mt.BudgetExceeded):
        m.enforce_ceiling(td)


def test_no_ceiling_means_no_enforcement(world):
    root, d, cap, task_id, td = world
    task = yaml.safe_load((td / "task.yaml").read_text())
    del task["budgets"]["model_cost_limit_usd"]
    (td / "task.yaml").write_text(yaml.safe_dump(task))
    m = mt.Meter(prices_path=root / "control/models/prices.yaml")
    m.record_usage(td, model="anthropic/claude-fable-5",
                   input_tokens=10_000_000, output_tokens=0)
    m.enforce_ceiling(td)  # no ceiling configured → no enforcement


# ------------------------------------------------------------- session pool

def test_cap_read_from_policies_not_constant(world):
    root, *_ = world
    pool = mt.SessionPool(policies_path=root / "control/models/policies.yaml")
    assert pool.cap == 2


def test_missing_cap_refused(tmp_path):
    p = tmp_path / "pol.yaml"
    p.write_text(yaml.safe_dump({"mode_s": {}}))
    with pytest.raises(mt.MeteringError, match="never a constant"):
        mt.SessionPool(policies_path=p)


def test_queue_above_cap_fifo(world):
    root, *_ = world
    pool = mt.SessionPool(policies_path=root / "control/models/policies.yaml")
    assert pool.request("TASK-001") is True
    assert pool.request("TASK-002") is True
    assert pool.request("TASK-003") is False   # queued, not failed
    assert pool.request("TASK-004") is False
    assert pool.release("TASK-001") == "TASK-003"   # FIFO
    assert pool.release("TASK-002") == "TASK-004"
    assert pool.release("TASK-003") is None


def test_slot_idempotent_per_task(world):
    root, *_ = world
    pool = mt.SessionPool(policies_path=root / "control/models/policies.yaml")
    assert pool.request("TASK-001") and pool.request("TASK-001")
    assert len(pool.active) == 1


# -- gate record commits (TASK-003 close finding, 2026-07-23) ----------------

def test_gate_record_file_committed_with_decision(world):
    """The record file itself must enter the commit lane — previously only
    state.yaml/log.jsonl (via transition) were committed and the record
    dangled in the working tree (TASK-003's six needed an owner push)."""
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    committer = d.committer
    n_before = len(committer.commits)
    record_path = cap.apply("PROJECT-000", ap.Decision(
        "APPROVE", task_id, "SAT", "msomali", "PR#9-review-1"))
    new = committer.commits[n_before:]
    record_commits = [(paths, msg) for paths, msg in new
                      if record_path in paths]
    assert record_commits, "gate record file never committed"
    paths, msg = record_commits[0]
    record = yaml.safe_load(record_path.read_text())
    assert record["gate_id"] in msg and "APPROVED" in msg
    # Order: record commit lands BEFORE the transition commit — a crash
    # between the two must leave a recorded decision, never an unrecorded
    # transition.
    transition_idx = next(i for i, (p, m) in enumerate(new) if "→" in m)
    record_idx = next(i for i, (p, m) in enumerate(new)
                      if record_path in p)
    assert record_idx < transition_idx


def test_reject_record_also_committed(world):
    root, d, cap, task_id, td = world
    advance(d, td, *TO_QUALITY)
    committer = d.committer
    n_before = len(committer.commits)
    record_path = cap.apply("PROJECT-000", ap.Decision(
        "REJECT", task_id, "SAT", "msomali", "PR#9"))
    new = committer.commits[n_before:]
    assert any(record_path in paths for paths, _ in new)
    assert any("REJECTED" in msg for _, msg in new)
