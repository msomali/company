"""Tests for metrics_weekly.py (B6.3) — throwaway git repos + fixtures."""
from __future__ import annotations

import datetime
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


def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "f.txt"], check=True)
    subprocess.run(
        [
            "git", "-C", str(tmp_path),
            "-c", "user.name=t", "-c", "user.email=t@t",
            "commit", "-q", "-m", "Merge pull request #40 from x/y",
        ],
        check=True,
    )
    return tmp_path


def test_git_merge_and_revert_counting(tmp_path):
    root = repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-q", "--allow-empty", "-m", 'Revert "bad change"'],
        check=True,
    )
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


def test_no_data_sections_say_so(tmp_path):
    root = repo(tmp_path)
    out = tmp_path / "reports"
    mw.main(["--until", "2026-07-17", "--root", str(root), "--out", str(out)])
    report = (out / "METRICS-2026-W29.md").read_text()
    assert "no decided gates" in report
    assert "no closed tasks" in report
    assert "idle-by-design" in report
