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
    lanes = tmp_path / "lanes"
    h = hv.GitHarvester(repo_root=tmp_path, runner=fake, push=True,
                        lanes_root=lanes)
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
    # ADR-B007: delivery worktree lives OUTSIDE the clone, under the shared
    # lanes root (/srv/company/lanes/.delivery/), never in-repo.
    wt = lanes / ".delivery" / "sde-TASK-9"
    assert (wt / "src/mod.py").read_bytes() == b"x = 1\n"
    assert (wt / "projects/P/episodes/TASK-9/handoff.md").read_text() == "body"
    assert not (tmp_path / ".delivery-worktrees").exists()


# -- unreadable inputs refuse, never crash (finding 3, req-1 gap) ------------

ROOT_SKIP = pytest.mark.skipif(
    os.geteuid() == 0, reason="root reads through any file mode")


@ROOT_SKIP
def test_collect_unreadable_file_refuses_not_crashes(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n"})
    (ws / "src/mod.py").chmod(0)
    try:
        with pytest.raises(hv.HarvestRefused, match="unreadable"):
            hv.collect(ws, ["src/mod.py"])
    finally:
        (ws / "src/mod.py").chmod(0o644)


@ROOT_SKIP
def test_run_harvest_unreadable_handoff_refuses(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    (ws / "handoff.md").chmod(0)
    spy = SpyHarvester()
    try:
        with pytest.raises(hv.HarvestRefused, match="handoff.md unreadable"):
            hv.run_harvest(repo_root=tmp_path, workspace=ws,
                           project_id="PROJECT-000", task_id="TASK-9",
                           role="SDE", required_outputs=["src/mod.py"],
                           harvester=spy)
    finally:
        (ws / "handoff.md").chmod(0o644)
    assert spy.calls == []


# -- front-matter stamp (finding 6) ------------------------------------------

import frontmatter_lint as fml  # noqa: E402
import yaml  # noqa: E402


def _harvest(tmp_path, ws, **kw):
    spy = SpyHarvester()
    kw.setdefault("required_outputs", ["src/mod.py"])
    hv.run_harvest(repo_root=tmp_path, workspace=ws, project_id="PROJECT-000",
                   task_id="TASK-9", role="SDE", harvester=spy, **kw)
    return spy


def test_stamp_replaces_agent_front_matter_and_passes_schema(tmp_path):
    body = "---\nbogus: true\nowner: wrong\n---\n\n" + valid_handoff()
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": body})
    spy = _harvest(tmp_path, ws, data_classification="confidential",
                   slug="titlecase")
    delivered = spy.calls[0]["handoff_body"]
    fm = yaml.safe_load(fml.extract_front_matter(delivered))
    assert fm["artifact_id"] == "projects/PROJECT-000/episodes/TASK-9/handoff.md"
    assert fm["title"] == "TASK-9 titlecase delivery handoff"
    assert fm["project"] == "PROJECT-000"
    assert fm["owner"].startswith("SDE")
    assert fm["sensitivity"] == "confidential"   # envelope data_classification
    assert fm["status"] == "READY_FOR_REVIEW"
    assert fml.schema_problems(fm) == []         # lint-clean by construction
    assert "bogus" not in delivered              # agent head fully replaced
    assert delivered.count("---\n") == 2         # exactly one fence remains
    assert "## 1." in delivered                  # ten-section body preserved
    assert "role: SAT" in delivered              # gate-claim line preserved


def test_stamp_without_agent_front_matter_defaults(tmp_path):
    ws = make_ws(tmp_path, {"src/mod.py": "x\n", "handoff.md": valid_handoff()})
    spy = _harvest(tmp_path, ws)
    delivered = spy.calls[0]["handoff_body"]
    fm = yaml.safe_load(fml.extract_front_matter(delivered))
    assert fm["sensitivity"] == "internal"       # default when envelope silent
    assert fm["title"] == "TASK-9 delivery handoff"
    assert fm["version"] == "1.0" and fm["type"] == "note"
    assert fml.schema_problems(fm) == []
    # stamping must not break the handoff_check authority CI re-runs
    assert hv.validate_handoff(delivered, "sde/TASK-9") == []


# -- delivered-.md front-matter pre-validation (finding 6, CI parity) --------

def test_delivered_md_bad_front_matter_refused(tmp_path):
    ws = make_ws(tmp_path, {
        "docs/x.md": "---\nartifact_id: 7\n---\nbody\n",
        "handoff.md": valid_handoff(),
    })
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="front matter fails"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9",
                       role="SDE", required_outputs=["docs/x.md"],
                       harvester=spy)
    assert spy.calls == []


def test_delivered_md_without_front_matter_ships(tmp_path):
    ws = make_ws(tmp_path, {"docs/x.md": "plain notes, no fence\n",
                            "handoff.md": valid_handoff()})
    spy = _harvest(tmp_path, ws, required_outputs=["docs/x.md"])
    assert [i.rel_path for i in spy.calls[0]["items"]] == ["docs/x.md"]


def test_delivered_md_required_dir_must_carry_front_matter(tmp_path):
    ws = make_ws(tmp_path, {
        "control/escalations/ESC-TASK-9.md": "no front matter here\n",
        "handoff.md": valid_handoff(),
    })
    spy = SpyHarvester()
    with pytest.raises(hv.HarvestRefused, match="required in this directory"):
        hv.run_harvest(repo_root=tmp_path, workspace=ws,
                       project_id="PROJECT-000", task_id="TASK-9", role="SDE",
                       required_outputs=["control/escalations/ESC-TASK-9.md"],
                       harvester=spy)
    assert spy.calls == []
