"""Tests for control/scripts/bootstrap-verify.sh (owner-requested standing
verifier). Hermetic: every case builds a fixture tree under tmp_path and points
the script at it via BOOTSTRAP_VERIFY_ROOT, so the suite is stable regardless of
the live repo's state. Mirrors the subprocess pattern of test_kill_switch.py.
"""
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "control/scripts/bootstrap-verify.sh"

ROLES = ["SAT", "SSE", "DPC", "DCE", "PJM", "HUMAN"]

# A "- [ ]" task that is genuinely N/A: carries BOTH an N/A token AND a §87
# disposition reference — the only shape the fail-safe rule accepts unchecked.
B22_NA = (
    "- [ ] B2.2 (H-EXEC) N/A (Mode P dormant, dispositioned N/A-dormant at §87) "
    "— CONDITIONAL, only on a Mode P reactivation ADR; Mode S active per "
    "ADR-B003. Ref: control/registers/section-87-phase-1-declaration.md"
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def make_green(root: Path) -> None:
    """A fixture tree that satisfies all six checks."""
    _write(root / "BOOTSTRAP-PLAN.md",
           "# BOOTSTRAP-PLAN\n\n"
           "- [x] B0.1 (H) done\n"
           "- [x] B2.1 (A) done\n"
           f"{B22_NA}\n"
           "- [x] B8.1 (H) done\n")
    rows = "".join(f"| {i} | item{i} | evidence | 2026-07-15 | [x] |\n"
                   for i in range(1, 10))
    _write(root / "control/sops/hardening-evidence.md",
           "| # | Item | Evidence | Date | Done |\n|---|---|---|---|---|\n"
           + rows + "\nAttested: all §85 hardening rows are now closed.\n")
    _write(root / "control/registers/section-87-phase-1-declaration.md", "decl\n")
    _write(root / "control/registers/section-b8.1-rotation-evidence.md", "rot\n")
    _write(root / "projects/PROJECT-000/episodes/TASK-001/manifest.yaml",
           "task_id: TASK-001\nfinal_state: CLOSED\n"
           "completeness:\n  complete: true\n")
    for role in ROLES:
        _write(root / f"projects/PROJECT-000/gates/GATE-TASK-001-{role}-1.yaml",
               f"gate_id: GATE-TASK-001-{role}-1\ngate_owner: {role}\n"
               "decision: APPROVED\n")


def run(root: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "BOOTSTRAP_VERIFY_ROOT": str(root)}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True,
                          text=True, env=env)


# --- green baseline --------------------------------------------------------
def test_green_tree_passes(tmp_path):
    make_green(tmp_path)
    p = run(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "GREEN" in p.stdout
    assert p.stdout.count("PASS") == 6
    assert "FAIL" not in p.stdout
    # B2.2 is reported as N/A, not done and not incomplete
    assert "N/A: B2.2" in p.stdout


# --- the N/A logic (item 1) — the core behaviour ---------------------------
def test_na_task_with_disposition_counts_satisfied(tmp_path):
    make_green(tmp_path)  # B2.2 is unchecked but N/A + §87 -> satisfied
    p = run(tmp_path)
    assert p.returncode == 0
    # green fixture: B0.1/B2.1/B8.1 done, B2.2 N/A-dispositioned, none incomplete
    assert "3 done, 1 N/A, 0 incomplete" in p.stdout


def test_unchecked_without_disposition_fails(tmp_path):
    """A bare unchecked box (no N/A / no §87) must FAIL — the fail-safe."""
    make_green(tmp_path)
    plan = tmp_path / "BOOTSTRAP-PLAN.md"
    plan.write_text(plan.read_text() + "- [ ] B9.9 (A) started, not finished\n")
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [1/6]" in p.stdout
    assert "B9.9" in p.stdout


def test_na_token_without_section87_fails(tmp_path):
    """N/A token alone (no §87 disposition ref) is NOT enough — strict AND."""
    make_green(tmp_path)
    _write(tmp_path / "BOOTSTRAP-PLAN.md",
           "# BOOTSTRAP-PLAN\n\n"
           "- [x] B0.1 (H) done\n"
           "- [ ] B2.2 (H-EXEC) N/A dormant, not built\n")  # no section-87/§87
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [1/6]" in p.stdout
    assert "B2.2" in p.stdout


def test_section87_ref_without_na_token_fails(tmp_path):
    """§87 reference alone (no N/A token) is NOT enough either — strict AND."""
    make_green(tmp_path)
    _write(tmp_path / "BOOTSTRAP-PLAN.md",
           "# BOOTSTRAP-PLAN\n\n"
           "- [x] B0.1 (H) done\n"
           "- [ ] B2.2 (H-EXEC) see section-87 declaration, pending build\n")
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [1/6]" in p.stdout


# --- checks 2..6 fail fixtures --------------------------------------------
def test_open_hardening_row_fails(tmp_path):
    make_green(tmp_path)
    f = tmp_path / "control/sops/hardening-evidence.md"
    f.write_text(f.read_text().replace(
        "| 9 | item9 | evidence | 2026-07-15 | [x] |",
        "| 9 | item9 | evidence | 2026-07-15 | [ ] |"))
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [2/6]" in p.stdout


def test_missing_phase1_declaration_fails(tmp_path):
    make_green(tmp_path)
    (tmp_path / "control/registers/section-87-phase-1-declaration.md").unlink()
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [3/6]" in p.stdout


def test_missing_rotation_evidence_fails(tmp_path):
    make_green(tmp_path)
    (tmp_path / "control/registers/section-b8.1-rotation-evidence.md").unlink()
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [4/6]" in p.stdout


def test_episode_not_closed_fails(tmp_path):
    make_green(tmp_path)
    m = tmp_path / "projects/PROJECT-000/episodes/TASK-001/manifest.yaml"
    m.write_text(m.read_text().replace("final_state: CLOSED",
                                       "final_state: OPERATIONS_AND_FEEDBACK"))
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [5/6]" in p.stdout


def test_missing_gate_fails(tmp_path):
    make_green(tmp_path)
    (tmp_path / "projects/PROJECT-000/gates/GATE-TASK-001-SAT-1.yaml").unlink()
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [6/6]" in p.stdout
    assert "SAT" in p.stdout


def test_gate_not_approved_fails(tmp_path):
    make_green(tmp_path)
    g = tmp_path / "projects/PROJECT-000/gates/GATE-TASK-001-DPC-1.yaml"
    g.write_text(g.read_text().replace("decision: APPROVED",
                                        "decision: REJECTED"))
    p = run(tmp_path)
    assert p.returncode != 0
    assert "FAIL  [6/6]" in p.stdout
    assert "DPC" in p.stdout
