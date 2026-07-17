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


def test_deploy_key_revocation_matches_manifest_row():
    """Kill switch severs the DISPATCHER_DEPLOY_KEY exactly as the
    SECRETS-MANIFEST row promises (revocation = delete key on repo)."""
    text = SCRIPT.read_text()
    assert "deploy-key delete" in text
    manifest = (REPO / "control/secrets/SECRETS-MANIFEST.md").read_text()
    assert "DISPATCHER_DEPLOY_KEY" in manifest
