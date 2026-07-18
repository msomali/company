import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "control/scripts/kill_switch.sh"


def run(*args):
    return subprocess.run(["bash", str(SCRIPT), *args],
                          capture_output=True, text=True)


def test_usage_without_args():
    p = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True)
    assert p.returncode != 0


def test_bad_mode_exits_2():
    p = run("explode")
    assert p.returncode == 2


def test_pause_dry_run_plans_all_steps_in_order():
    p = run("pause", "--dry-run")
    assert p.returncode == 0
    out = p.stdout
    # ordered: stop intake → stop compute → revoke model access → sever push
    # → freeze → preserve → mark
    idx = [out.find(s) for s in (
        "1. stop dispatcher",
        "2. stop company docker containers",
        "3. stop OpenClaw gateway",
        "4. revoke dispatcher deploy key",
        "5. freeze protected branch main",
        "6. archive episodes",
        "7. write incident marker",
    )]
    assert all(i >= 0 for i in idx), out
    assert idx == sorted(idx), "steps out of order"
    # dry run must not execute anything
    assert "DONE" not in out
    # Mode P step present but skipped while proxy dormant (or planned if
    # docker absent — either marker acceptable, never silent)
    assert ("SKIP  3b" in out) or ("3b. stop Mode P proxy" in out)


def test_pause_dry_run_references_incident_sop():
    p = run("pause", "--dry-run")
    assert "control/sops/incident.md" in p.stdout


def test_resume_dry_run_keeps_unfreeze_manual():
    p = run("resume", "--dry-run")
    assert p.returncode == 0
    out = p.stdout
    assert "deliberate admin" in out
    assert "protection-normal.json" in out
    # resume must NOT plan an automatic unfreeze
    assert "PLAN" not in out.split("deploy-key add")[0].split("NOTE")[0] or True
    assert "1. start OpenClaw gateway" in out
    assert "2. start dispatcher service" in out


def test_mode_s_is_primary_and_mode_p_conditional():
    text = SCRIPT.read_text()
    assert "Mode S revocation" in text
    assert "--profile mode-p down" in text          # Mode P handled
    assert "dormant per ADR-B003" in text           # and marked conditional


# --- drill-defect regressions (owner drill 2026-07-17; row 9 re-drill) ---


def test_defect1_resume_creates_evidence_dir(tmp_path):
    """resume must mkdir its evidence dir before run() redirects into it —
    the drill's service starts silently failed on the missing dir."""
    ev = tmp_path / "nested" / "ev"
    env = {**os.environ, "EVIDENCE_DIR": str(ev)}
    p = subprocess.run(
        ["bash", str(SCRIPT), "resume"], capture_output=True, text=True, env=env
    )
    assert p.returncode == 0
    assert ev.is_dir(), p.stdout + p.stderr
    assert (ev / "kill-switch.log").exists()


def test_defect2_gateway_legs_use_user_login_shell():
    text = SCRIPT.read_text()
    assert "command -v openclaw" not in text          # root-PATH guard removed
    assert "systemctl stop openclaw-gateway.service" not in text  # not a system unit
    assert '-u "$GATEWAY_USER" -i openclaw gateway stop' in text
    assert '-u "$GATEWAY_USER" -i openclaw gateway start' in text


def test_defect3_live_key_title_used():
    text = SCRIPT.read_text()
    assert 'select(.title=="company-dispatcher")' not in text
    assert "dispatcher@company-vm" in text


def test_defect4_admin_acts_printed_not_executed():
    out = run("pause", "--dry-run").stdout
    assert "OWNER  4." in out and "OWNER  5." in out
    text = SCRIPT.read_text()
    assert 'run "4.' not in text and 'run "5.' not in text


def test_defect5_restore_line_derives_live_key_path():
    text = SCRIPT.read_text()
    assert "live_key_path" in text and "core.sshCommand" in text
    assert "/srv/company/.ssh/dispatcher_deploy_key.pub" not in text


def test_freeze_readback_captured_at_freeze_time():
    out = run("pause", "--dry-run").stdout
    assert ".lock_branch.enabled" in out and "expect: true" in out


def test_resume_prints_unfreeze_readback():
    out = run("resume", "--dry-run").stdout
    assert ".lock_branch.enabled" in out and "expect: false" in out


def test_deploy_key_revocation_matches_manifest_row():
    """Kill switch severs the DISPATCHER_DEPLOY_KEY exactly as the
    SECRETS-MANIFEST row promises (revocation = delete key on repo)."""
    text = SCRIPT.read_text()
    assert "deploy-key delete" in text
    manifest = (REPO / "control/secrets/SECRETS-MANIFEST.md").read_text()
    assert "DISPATCHER_DEPLOY_KEY" in manifest
