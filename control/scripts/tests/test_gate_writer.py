"""Tests for gate_writer.py (B5.2) — offline: event/reviews from fixtures,
no network, no git side effects (--out-dir keeps runs write-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import gate_writer as gw  # noqa: E402
import handoff_check as hc  # noqa: E402


def pr_payload(**over):
    pr = {
        "number": 42,
        "title": "B9.9: sample deliverable",
        "body": "## 9. Next owner\nHuman owner (merge, then drill).\n",
        "merged": True,
        "merged_at": "2026-07-17T18:00:00Z",
        "merge_commit_sha": "abcdef0123456789",
        "html_url": "https://github.com/msomali/company/pull/42",
        "head": {"ref": "bootstrap/b9.9-sample"},
    }
    pr.update(over)
    return pr


def reviews_payload():
    return [
        {
            "state": "APPROVED",
            "body": "role: SAT\nGate review: criteria verified.\n- Finding: none blocking",
            "html_url": "https://github.com/msomali/company/pull/42#pullrequestreview-1",
        },
        {
            "state": "COMMENTED",
            "body": "drive-by comment",
            "html_url": "https://github.com/msomali/company/pull/42#pullrequestreview-2",
        },
    ]


def run_offline(tmp_path, pr, reviews):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": pr}))
    rv = tmp_path / "reviews.json"
    rv.write_text(json.dumps(reviews))
    out = tmp_path / "gates"
    code = gw.main(
        ["--event", str(event), "--reviews", str(rv), "--out-dir", str(out)]
    )
    return code, out


def test_record_written_and_schema_valid(tmp_path):
    code, out = run_offline(tmp_path, pr_payload(), reviews_payload())
    assert code == 0
    files = list(out.glob("GATE-*.yaml"))
    assert len(files) == 1
    record = yaml.safe_load(files[0].read_text())
    assert record["gate_id"] == "GATE-SAT-PR42-abcdef01"
    assert record["gate_owner"] == "SAT"
    assert record["decision"] == "APPROVED"
    assert record["next_owner"] == "Human owner (merge, then drill)."
    assert record["approval_message_ref"].endswith("pullrequestreview-1")
    assert any(e.startswith("merge:abcdef") for e in record["evidence"])


def test_no_role_claim_falls_back_to_human(tmp_path):
    reviews = [{"state": "APPROVED", "body": "looks correct", "html_url": "x"}]
    code, out = run_offline(tmp_path, pr_payload(body=""), reviews)
    assert code == 0
    record = yaml.safe_load(next(out.glob("GATE-*.yaml")).read_text())
    assert record["gate_owner"] == "HUMAN"
    assert record["next_owner"] == "human owner"


def test_unmerged_close_emits_nothing(tmp_path):
    code, out = run_offline(tmp_path, pr_payload(merged=False), [])
    assert code == 0
    assert not out.exists()


def test_gate_head_recursion_guard(tmp_path):
    code, out = run_offline(
        tmp_path, pr_payload(head={"ref": "gate/pr-41"}), reviews_payload()
    )
    assert code == 0
    assert not out.exists()


def test_missing_event_is_benign():
    assert gw.main(["--event", "/nonexistent/event.json"]) == 0


def test_replay_by_pr_number(tmp_path, monkeypatch):
    """workflow_dispatch replay: no pull_request in the event — PR fetched
    from the API by number (owner requirement after the consumed #23 event)."""
    monkeypatch.setattr(gw, "gh_api", lambda path, token: pr_payload())
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"inputs": {"pr_number": "42"}}))
    rv = tmp_path / "reviews.json"
    rv.write_text(json.dumps(reviews_payload()))
    out = tmp_path / "gates"
    code = gw.main(
        ["--event", str(event), "--reviews", str(rv), "--out-dir", str(out)]
    )
    assert code == 0
    assert (out / "GATE-SAT-PR42-abcdef01.yaml").is_file()


def test_replay_cli_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(gw, "gh_api", lambda path, token: pr_payload())
    rv = tmp_path / "reviews.json"
    rv.write_text(json.dumps(reviews_payload()))
    out = tmp_path / "gates"
    code = gw.main(
        ["--event", "/nonexistent", "--pr", "42", "--reviews", str(rv), "--out-dir", str(out)]
    )
    assert code == 0
    assert list(out.glob("GATE-*.yaml"))


def test_replay_fetch_failure_exits_1(tmp_path, monkeypatch):
    def boom(path, token):
        raise OSError("api down")

    monkeypatch.setattr(gw, "gh_api", boom)
    assert gw.main(["--event", "/nonexistent", "--pr", "42"]) == 1


def test_role_claim_parsing():
    assert gw.claimed_role(["role: SAT\nverdict ok"]) == "SAT"
    assert gw.claimed_role(["GATE-DCE attribution here"]) == "DCE"
    assert gw.claimed_role(["approve, no claim"]) == "HUMAN"
    # SSE claim in second text after unclaimed first
    assert gw.claimed_role(["plain", "role: SSE"]) == "SSE"


def test_gate_pr_body_passes_handoff_check(tmp_path):
    pr = pr_payload()
    record = gw.build_gate_record(pr, reviews_payload())
    body = gw.gate_pr_body(record, pr["number"])
    assert hc.check(body) == []


def test_invalid_record_blocks(tmp_path):
    record = gw.build_gate_record(pr_payload(title=None), reviews_payload())
    record["decision"] = "MAYBE"
    import jsonschema

    validator = jsonschema.Draft7Validator(
        json.loads((gw.GATE_SCHEMA).read_text())
    )
    assert list(validator.iter_errors(record))
