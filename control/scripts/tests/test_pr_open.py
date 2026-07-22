"""pr_open — the refusal path must open nothing; the green path opens exactly once."""
from pathlib import Path

import pr_open

REPO = Path(__file__).resolve().parents[3]

TEMPLATE = (REPO / ".github/pull_request_template.md").read_text()


def filled_body() -> str:
    out = []
    for line in TEMPLATE.splitlines():
        out.append(line)
        if line.startswith("## "):
            out.append("Real content for this section.")
    return "\n".join(out)


class SpyCreate:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {"html_url": "https://example.test/pr/1", "number": 1}


def run(tmp_path, body: str, head: str, token: str | None = "dummy-token"):
    body_file = tmp_path / "body.md"
    body_file.write_text(body)
    token_file = tmp_path / "gh-token"
    if token is not None:
        token_file.write_text(token + "\n")
    # token_file may deliberately not exist: the refusal path must never need it
    spy = SpyCreate()
    rc = pr_open.main(
        [
            "--title", "T",
            "--body-file", str(body_file),
            "--head", head,
            "--base", "main",
            "--repo", "owner/repo",
            "--token-file", str(token_file),
        ],
        create=spy,
    )
    return rc, spy


def test_refuses_checker_failing_body_and_creates_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    # token=None: the token file does not exist — proves refusal happens
    # before any secret is read and before any network-shaped call.
    rc, spy = run(tmp_path, "not a handoff body\n", "fix/anything", token=None)
    assert rc == 2
    assert spy.calls == []


def test_refuses_single_empty_section(tmp_path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    body = filled_body().replace("## 10. Out of scope\nReal content for this section.",
                                 "## 10. Out of scope")
    rc, spy = run(tmp_path, body, "fix/anything", token=None)
    assert rc == 2
    assert spy.calls == []


def test_refuses_role_branch_without_role_claim(tmp_path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    rc, spy = run(tmp_path, filled_body(), "sde/TASK-999", token=None)
    assert rc == 2
    assert spy.calls == []


def test_opens_exactly_once_on_green_body(tmp_path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    rc, spy = run(tmp_path, filled_body(), "fix/anything")
    assert rc == 0
    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["repo"] == "owner/repo"
    assert call["token"] == "dummy-token"
    assert call["payload"]["head"] == "fix/anything"
    assert call["payload"]["base"] == "main"
    assert call["payload"]["title"] == "T"
    assert call["payload"]["body"] == filled_body()


def test_role_branch_with_claim_passes(tmp_path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    rc, spy = run(tmp_path, filled_body() + "\nrole: SAT\n", "sde/TASK-999")
    assert rc == 0
    assert len(spy.calls) == 1
