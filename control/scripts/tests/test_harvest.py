"""harvest (ADR-B006) — refusals are loud and total; only declared outputs ship."""
import os
from pathlib import Path

import pytest

import harvest as hv

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = (REPO / ".github/pull_request_template.md").read_text()


def valid_handoff() -> str:
    out = []
    for line in TEMPLATE.splitlines():
        out.append(line)
        if line.startswith("## "):
            out.append("Real content for this section.")
    out.append("role: SAT")  # role-prefixed delivery branches need the claim
    return "\n".join(out)


def make_ws(tmp_path: Path, files: dict[str, str]) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    for rel, content in files.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return ws


class SpyHarvester:
    def __init__(self):
        self.calls = []

    def deliver(self, **kwargs):
        self.calls.append(kwargs)
        return "f" * 40


# -- collect ---------------------------------------------------------------

def test_collect_happy_path(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x = 1\n", "tests/test_mod.py": "ok\n"})
    items = hv.collect(ws, ["src/mod.py", "tests/test_mod.py"])
    assert [i.rel_path for i in items] == ["src/mod.py", "tests/test_mod.py"]
    assert items[0].data == b"x = 1\n"


def test_collect_missing_output_refuses_whole_harvest(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n"})
    with pytest.raises(hv.HarvestRefused, match="missing"):
        hv.collect(ws, ["src/mod.py", "tests/test_mod.py"])


def test_collect_empty_manifest_refuses(tmp_path):
    ws = make_ws(tmp_path, {})
    with pytest.raises(hv.HarvestRefused, match="no required_outputs"):
        hv.collect(ws, [])


def test_collect_traversal_refused(tmp_path):
    ws = make_ws(tmp_path, {})
    (tmp_path / "outside.txt").write_text("secret")
    with pytest.raises(hv.HarvestRefused, match="traversal"):
        hv.collect(ws, ["../outside.txt"])


def test_collect_absolute_path_refused(tmp_path):
    ws = make_ws(tmp_path, {})
    with pytest.raises(hv.HarvestRefused, match="absolute"):
        hv.collect(ws, ["/etc/passwd"])


def test_collect_symlink_escape_refused(tmp_path):
    ws = make_ws(tmp_path, {})
    (tmp_path / "outside.txt").write_text("outside")
    os.symlink(tmp_path / "outside.txt", ws / "sneaky.txt")
    with pytest.raises(hv.HarvestRefused, match="escapes the workspace"):
        hv.collect(ws, ["sneaky.txt"])


def test_collect_oversize_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(hv, "MAX_FILE_BYTES", 4)
    ws = make_ws(tmp_path, {"big.txt": "12345"})
    with pytest.raises(hv.HarvestRefused, match="delivery cap"):
        hv.collect(ws, ["big.txt"])


# -- secret scan (binding requirement 2) ------------------------------------

def test_secret_scan_hits_and_never_echoes_value(tmp_path):
    leaked = "sk-ant-oat01-" + "a" * 24
    ws = make_ws(tmp_path, {"src/cfg.py": f"TOKEN = '{leaked}'\n"})
    items = hv.collect(ws, ["src/cfg.py"])
    findings = hv.secret_scan(items)
    assert findings == ["src/cfg.py: anthropic-token"]
    assert leaked not in " ".join(findings)


def test_secret_scan_private_key_block(tmp_path):
    ws = make_ws(tmp_path, {"key.pem": "-----BEGIN RSA PRIVATE KEY-----\n"})
    items = hv.collect(ws, ["key.pem"])
    assert hv.secret_scan(items) == ["key.pem: private-key-block"]


def test_run_harvest_secret_hit_refuses_before_any_git(tmp_path):
    leaked = "ghp_" + "b" * 24
    ws = make_ws(tmp_path, {"src/mod.py": f"# {leaked}\n",
                            "handoff.md": valid_handoff()})
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="secret scan hit"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9",
                       role="SDE", required_outputs=["src/mod.py"],
                       harvester=spy)
    assert spy.calls == []


# -- handoff pre-validation (binding requirement 1 fires dispatcher-side) ---

def test_run_harvest_missing_handoff_refuses(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n"})
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="no handoff.md"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9",
                       role="SDE", required_outputs=["src/mod.py"],
                       harvester=spy)
    assert spy.calls == []


def test_run_harvest_invalid_handoff_refuses(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n",
                            "handoff.md": "not ten sections"})
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="fails handoff_check"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9",
                       role="SDE", required_outputs=["src/mod.py"],
                       harvester=spy)
    assert spy.calls == []


def test_run_harvest_role_claim_enforced_for_role_branch(tmp_path):
    body = valid_handoff().replace("role: SAT", "")
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": body})
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="role claim"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9",
                       role="SDE", required_outputs=["src/mod.py"],
                       harvester=spy)
    assert spy.calls == []


# -- happy path --------------------------------------------------------------

def test_run_harvest_happy_path_delivers_declared_plus_handoff(tmp_path):
    ws = make_ws(tmp_path, {
        "src/mod.py": "x = 1\n",
        "tests/test_mod.py": "ok\n",
        "handoff.md": valid_handoff(),
        "scratch/notes.txt": "NOT declared — must not ship",
    })
    spy = SpyHarvester()
    result = hv.run_harvest(repo_root=tmp_path, workspace=ws,
                            project_id="PROJECT-000", task_id="TASK-9",
                            role="SDE",
                            required_outputs=["src/mod.py", "tests/test_mod.py"],
                            harvester=spy)
    assert result["branch"] == "sde/TASK-9"
    assert result["sha"] == "f" * 40
    call = spy.calls[0]
    shipped = [i.rel_path for i in call["items"]]
    assert shipped == ["src/mod.py", "tests/test_mod.py"]
    assert "scratch/notes.txt" not in shipped
    assert call["handoff_rel"] == "projects/PROJECT-000/episodes/TASK-9/handoff.md"
    assert call["task_id"] == "TASK-9" and call["role"] == "SDE"
    assert result["files"][-1].endswith("handoff.md")


def test_run_harvest_slug_suffixes_branch(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    spy = SpyHarvester()
    result = hv.run_harvest(repo_root=tmp_path, workspace=ws,
                            project_id="PROJECT-000", task_id="TASK-9",
                            role="SDE", required_outputs=["src/mod.py"],
                            slug="titlecase", harvester=spy)
    assert result["branch"] == "sde/TASK-9-titlecase"


# -- GitHarvester plumbing (offline; fake runner) ----------------------------

class FakeGit:
    """Records git argv; simulates missing branch and a rev-parse sha."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd, env=None):
        self.calls.append(argv)
        if argv[1:3] == ["rev-parse", "--verify"] or \
           argv[1:4] == ["rev-parse", "--verify", "--quiet"]:
            return 1, "", ""          # branch does not exist yet
        if "rev-parse" in argv and "HEAD" in argv:
            return 0, "c0ffee1234deadbeef\n", ""
        return 0, "", ""


def test_git_harvester_sequence_and_provenance(tmp_path):
    fake = FakeGit()
    h = hv.GitHarvester(repo_root=tmp_path, runner=fake, push=True)
    items = [hv.Collected("src/mod.py", tmp_path / "x", b"x = 1\n")]
    sha = h.deliver(branch="sde/TASK-9", items=items,
                    handoff_rel="projects/P/episodes/TASK-9/handoff.md",
                    handoff_body="body", task_id="TASK-9", role="SDE")
    assert sha == "c0ffee1234deadbeef"
    flat = ["\x00".join(c) for c in fake.calls]
    assert any("fetch\x00origin\x00main" in f for f in flat)
    assert any("worktree" in f and "-b\x00sde/TASK-9" in f for f in flat)
    commit = next(c for c in fake.calls if "commit" in c)
    assert f"--author={hv.BOT_NAME} <{hv.BOT_EMAIL}>" in commit
    assert f"user.name={hv.DISPATCHER_NAME}" in commit
    push = next(c for c in fake.calls if "push" in c)
    assert push[-1] == "sde/TASK-9"
    # worktree is always removed, success or not
    assert any("worktree" in c and "remove" in c for c in fake.calls)
    # files were materialized into the worktree before add
    wt = tmp_path / ".delivery-worktrees" / "sde-TASK-9"
    assert (wt / "src/mod.py").read_bytes() == b"x = 1\n"
    assert (wt / "projects/P/episodes/TASK-9/handoff.md").read_text() == "body"
