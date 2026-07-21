"""Tests for metrics_weekly.py (B6.3) — throwaway git repos + fixtures."""
from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import metrics_weekly as mw  # noqa: E402

UNTIL = datetime.date(2026, 7, 17)
GATE = """\
gate_id: GATE-SAT-PR40-aaaaaaaa
artifact_or_release: "PR #40: sample"
gate_owner: SAT
decision: {decision}
criteria_version: v1
evidence: [x]
next_owner: human
decided_at: "{decided}"
"""
ESC = """\
---
artifact_id: control/escalations/{name}.md
title: t
type: escalation
project: control
owner: bootstrap
version: "1.0"
status: APPROVED
sensitivity: internal
created: {created}
updated: {created}
---
body
"""


# Commit timestamps are PINNED (env below): tests once created commits at
# wall-clock "now" against a fixed window and broke the moment UTC rolled
# past midnight (found 2026-07-17 late PDT). Determinism or it didn't happen.
GIT_DATE_ENV = {
    "GIT_AUTHOR_DATE": "2026-07-16T12:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-07-16T12:00:00 +0000",
}


def commit(root: Path, message: str, *extra: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-q", *extra, "-m", message],
        check=True,
        env={**os.environ, **GIT_DATE_ENV},
    )


def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "f.txt"], check=True)
    commit(tmp_path, "Merge pull request #40 from x/y")
    return tmp_path


def test_git_merge_and_revert_counting(tmp_path):
    root = repo(tmp_path)
    commit(root, 'Revert "bad change"', "--allow-empty")
    g = mw.collect_git(root, UNTIL - datetime.timedelta(days=6), UNTIL)
    assert g["merge_count"] == 1 and g["merged_prs"] == [40]
    assert g["revert_count"] == 1


def test_gate_rejection_rate(tmp_path):
    gates = tmp_path / "gates"
    gates.mkdir()
    (gates / "GATE-a.yaml").write_text(GATE.format(decision="APPROVED", decided="2026-07-16T01:00:00Z"))
    (gates / "GATE-b.yaml").write_text(
        GATE.format(decision="CHANGES_REQUIRED", decided="2026-07-15T01:00:00Z").replace("PR40", "PR41")
    )
    (gates / "GATE-old.yaml").write_text(
        GATE.format(decision="REJECTED", decided="2026-01-01T01:00:00Z")
    )
    ga = mw.collect_gates(tmp_path, UNTIL - datetime.timedelta(days=6), UNTIL)
    assert ga["decided"] == 2
    assert ga["rejection_rate"] == 0.5
    assert ga["by_owner"] == {"SAT": 2}


def test_escalation_window(tmp_path):
    esc = tmp_path / "control" / "escalations"
    esc.mkdir(parents=True)
    (esc / "ESC-B001.md").write_text(ESC.format(name="ESC-B001", created="2026-07-15"))
    (esc / "INC-001.md").write_text(ESC.format(name="INC-001", created="2026-07-16"))
    (esc / "ESC-OLD.md").write_text(ESC.format(name="ESC-OLD", created="2026-01-01"))
    e = mw.collect_escalations(tmp_path, UNTIL - datetime.timedelta(days=6), UNTIL)
    assert e == {"ESC": 1, "INC": 1}


def test_tasks_no_episodes_dir(tmp_path):
    t = mw.collect_tasks(tmp_path, UNTIL - datetime.timedelta(days=6), UNTIL)
    assert t["packages"] == 0 and "idle-by-design" in t["note"]


def test_tasks_with_episode_and_cost(tmp_path):
    (tmp_path / "control" / "models").mkdir(parents=True)
    (tmp_path / "control" / "models" / "prices.yaml").write_text(
        "as_of: 2026-07-16\nmodels:\n  m/x: {input_per_mtok: 10.0, output_per_mtok: 50.0}\n"
    )
    task = tmp_path / "episodes" / "TASK-001"
    task.mkdir(parents=True)
    (task / "state.yaml").write_text(
        "status: DONE\nhistory:\n"
        "  - {at: '2026-07-16T10:00:00Z', to: INTAKE}\n"
        "  - {at: '2026-07-16T10:30:00Z', to: DONE}\n"
    )
    (task / "usage.yaml").write_text(
        "calls:\n  - {model: m/x, input_tokens: 1000000, output_tokens: 100000}\n"
    )
    t = mw.collect_tasks(tmp_path, UNTIL - datetime.timedelta(days=6), UNTIL)
    assert t["done"] == 1 and t["success_rate"] == 1.0
    assert t["latency_minutes_median"] == 30.0
    assert t["estimated_cost_usd"] == 15.0


def test_projects_episodes_layout_and_metering_usage_format(tmp_path):
    """§88.11 fix: episodes under projects/<P>/episodes/ are found, and
    metering.py's real usage.yaml format (totals + calls:int) is priced
    from its record-time totals."""
    (tmp_path / "control/models").mkdir(parents=True)
    (tmp_path / "control/models/prices.yaml").write_text(
        "as_of: 2026-07-16\nmodels:\n  m/x: {input_per_mtok: 10.0, output_per_mtok: 50.0}\n"
    )
    task = tmp_path / "projects/PROJECT-000/episodes/TASK-001"
    task.mkdir(parents=True)
    (task / "state.yaml").write_text(
        "task_id: TASK-001\nstate: DEPLOYMENT\nhistory:\n"
        "  - {at: '2026-07-17T10:00:00Z', from: NONE, to: INTAKE, evidence: e}\n"
        "  - {at: '2026-07-17T10:30:00Z', from: INTAKE, to: DISCOVERY, evidence: e}\n"
    )
    (task / "usage.yaml").write_text(
        "total_input_tokens: 3456\ntotal_output_tokens: 2531\n"
        "total_estimated_cost_usd: 0.16111\ncalls: 2\nprices_as_of: '2026-07-16'\n"
    )
    t = mw.collect_tasks(
        tmp_path, datetime.date(2026, 7, 12), datetime.date(2026, 7, 18)
    )
    assert t["packages"] == 1 and t["in_flight"] == 1
    assert t["tokens_input"] == 3456 and t["tokens_output"] == 2531
    assert t["estimated_cost_usd"] == 0.1611  # rounded, from record-time totals


def test_calls_int_does_not_crash(tmp_path):
    """Regression: metering's calls-as-int counter must never be iterated."""
    task = tmp_path / "projects/P/episodes/TASK-009"
    task.mkdir(parents=True)
    (task / "state.yaml").write_text(
        "task_id: TASK-009\nstate: INTAKE\nhistory:\n"
        "  - {at: '2026-07-17T10:00:00Z', from: NONE, to: INTAKE, evidence: e}\n"
    )
    (task / "usage.yaml").write_text("calls: 3\ntotal_input_tokens: 10\n")
    t = mw.collect_tasks(
        tmp_path, datetime.date(2026, 7, 12), datetime.date(2026, 7, 18)
    )
    assert t["tokens_input"] == 10 and t["estimated_cost_usd"] == 0.0


def test_report_written_with_front_matter(tmp_path):
    root = repo(tmp_path)
    out = tmp_path / "reports"
    assert mw.main(["--until", "2026-07-17", "--root", str(root), "--out", str(out)]) == 0
    report = (out / "METRICS-2026-W29.md").read_text()
    assert report.startswith("---\nartifact_id: METRICS-2026-W29")
    assert "| Merged PRs (main, first-parent) | 1 (#40) |" in report
    # machine block parses back
    yaml_block = report.split("```yaml\n")[1].split("```")[0]
    metrics = yaml.safe_load(yaml_block)
    assert metrics["git"]["merge_count"] == 1


def test_overwrite_refused_without_force_and_writes_nothing(tmp_path, capsys):
    """The load-bearing property: an existing weekly report + no --force must
    refuse with non-zero exit and leave the file byte-for-byte unchanged (a
    silent clobber destroyed the real W29 report during B6.3 check 11;
    RUNBOOK-B7.2)."""
    root = repo(tmp_path)
    out = tmp_path / "reports"
    out.mkdir()
    target = out / "METRICS-2026-W29.md"
    original = b"SIGNED ARTIFACT \xe2\x80\x94 committed W29 report, not scratch\n"
    target.write_bytes(original)
    rc = mw.main(["--until", "2026-07-17", "--root", str(root), "--out", str(out)])
    assert rc != 0
    assert target.read_bytes() == original  # refuse writes NOTHING
    err = capsys.readouterr().err
    assert "REFUSING to overwrite existing" in err
    assert str(target) in err
    assert "--force" in err


def test_overwrite_with_force_warns_and_overwrites(tmp_path, capsys):
    root = repo(tmp_path)
    out = tmp_path / "reports"
    out.mkdir()
    target = out / "METRICS-2026-W29.md"
    target.write_text("stale report\n")
    rc = mw.main(
        ["--until", "2026-07-17", "--root", str(root), "--out", str(out), "--force"]
    )
    assert rc == 0
    assert target.read_text().startswith("---\nartifact_id: METRICS-2026-W29")
    err = capsys.readouterr().err
    assert "WARNING overwriting existing" in err
    assert str(target) in err


def test_fresh_path_writes_without_warning(tmp_path, capsys):
    root = repo(tmp_path)
    out = tmp_path / "reports"
    assert mw.main(["--until", "2026-07-17", "--root", str(root), "--out", str(out)]) == 0
    assert (out / "METRICS-2026-W29.md").is_file()
    err = capsys.readouterr().err
    assert "REFUSING" not in err and "WARNING" not in err


def test_no_data_sections_say_so(tmp_path):
    root = repo(tmp_path)
    out = tmp_path / "reports"
    mw.main(["--until", "2026-07-17", "--root", str(root), "--out", str(out)])
    report = (out / "METRICS-2026-W29.md").read_text()
    assert "no decided gates" in report
    assert "no closed tasks" in report
    assert "idle-by-design" in report
