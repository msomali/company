import copy
from pathlib import Path

import pytest
import yaml

import manifest_generator as mg

REPO = Path(__file__).resolve().parents[3]

VALID = {
    "agent_id": "SDE",
    "name": "Senior Software Development Engineer",
    "agent_version": "1.1.0",
    "role_contract_version": "v1.1",
    "owner": "human-owner",
    "status": "contract-only",
    "model_policy": "reasoning-max",
    "prompt_bundle_version": "sde-prompts-1.0.0",
    "session_pattern": "dedicated-channel",
    "pilot_status": "ACTIVE",
    "allowed_tools": ["repository.read", "repository.write_scoped", "test.run"],
    "denied_tools": ["production.deploy", "external.communicate"],
    "memory_policy": "project-engineering",
    "risk_ceiling": "high-with-human-approval",
    "required_evals": ["implementation_correctness"],
    "role_contract": {
        "identity": "The engineer who turns approved designs into working code.",
        "mission": "Ship correct, reviewed, tested increments.",
        "principles": ["Small steps", "Tests first where practical"],
        "responsibilities": ["Implement approved tasks", "Keep CI green"],
        "collaboration": ["SAA for architecture", "SAT reviews all artifacts"],
        "escalation": ["Blocked > 2h -> PJM", "Security question -> SSE"],
    },
}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "control/manifests").mkdir(parents=True)
    (tmp_path / "control/schemas").mkdir(parents=True)
    (tmp_path / "control/models").mkdir(parents=True)
    (tmp_path / "company").mkdir()
    (tmp_path / "control/schemas/manifest.json").write_text(
        (REPO / "control/schemas/manifest.json").read_text()
    )
    (tmp_path / "company/digest-v1.1.md").write_text(
        (REPO / "company/digest-v1.1.md").read_text()
    )
    (tmp_path / "control/models/policies.yaml").write_text(
        (REPO / "control/models/policies.yaml").read_text()
    )
    monkeypatch.setattr(mg, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mg, "MANIFEST_DIR", tmp_path / "control/manifests")
    monkeypatch.setattr(mg, "GENERATED_DIR", tmp_path / "control/manifests/_generated")
    monkeypatch.setattr(mg, "SCHEMA_PATH", tmp_path / "control/schemas/manifest.json")
    monkeypatch.setattr(mg, "DIGEST_PATH", tmp_path / "company/digest-v1.1.md")
    monkeypatch.setattr(mg, "POLICIES_PATH", tmp_path / "control/models/policies.yaml")
    return tmp_path


def write_manifest(repo: Path, data: dict, name: str | None = None) -> Path:
    path = repo / "control/manifests" / (name or f"{data['agent_id'].lower()}.yaml")
    path.write_text(yaml.safe_dump(data))
    return path


def test_valid_manifest_generates_four_files(repo):
    write_manifest(repo, VALID)
    assert mg.main([]) == 0
    for fname in ("IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md"):
        out = repo / "control/manifests/_generated/SDE" / fname
        assert out.exists(), fname
        assert out.read_text().startswith(mg.HEADER), fname


def test_determinism_byte_identical(repo):
    write_manifest(repo, VALID)
    assert mg.main([]) == 0
    first = {
        p: p.read_bytes()
        for p in (repo / "control/manifests/_generated").rglob("*.md")
    }
    assert mg.main([]) == 0
    second = {
        p: p.read_bytes()
        for p in (repo / "control/manifests/_generated").rglob("*.md")
    }
    assert first == second and first


def test_check_mode_detects_stale_and_orphan(repo):
    write_manifest(repo, VALID)
    assert mg.main([]) == 0
    assert mg.main(["--check"]) == 0
    # stale
    target = repo / "control/manifests/_generated/SDE/TOOLS.md"
    target.write_text(target.read_text() + "hand edit\n")
    assert mg.main(["--check"]) == 1
    # orphan
    assert mg.main([]) == 0
    orphan = repo / "control/manifests/_generated/ZZZ/AGENTS.md"
    orphan.parent.mkdir()
    orphan.write_text("orphan")
    assert mg.main(["--check"]) == 1


def test_digest_embedded_verbatim_with_substitution(repo):
    write_manifest(repo, VALID)
    assert mg.main([]) == 0
    agents = (repo / "control/manifests/_generated/SDE/AGENTS.md").read_text()
    digest = (repo / "company/digest-v1.1.md").read_text()
    expected = digest.replace("{ROLE_ID}", "SDE").replace(
        "{ROLE_NAME}", "Senior Software Development Engineer"
    )
    assert expected in agents
    assert "{ROLE_ID}" not in agents
    assert "## Universal Working Method (v1 §10)" in agents


def test_missing_required_field_fails(repo):
    bad = copy.deepcopy(VALID)
    del bad["role_contract"]
    write_manifest(repo, bad)
    assert mg.main([]) == 1


def test_unknown_model_policy_fails(repo):
    bad = copy.deepcopy(VALID)
    bad["model_policy"] = "nonexistent-policy"
    write_manifest(repo, bad)
    assert mg.main([]) == 1


def test_filename_must_match_agent_id(repo):
    write_manifest(repo, VALID, name="wrong-name.yaml")
    assert mg.main([]) == 1


def test_duplicate_agent_id_fails(repo):
    write_manifest(repo, VALID)
    other = copy.deepcopy(VALID)
    write_manifest(repo, other, name="sde2.yaml")  # same agent_id, other file
    assert mg.main([]) == 1


def test_deny_wins_on_overlap(repo):
    m = copy.deepcopy(VALID)
    m["allowed_tools"] = ["repository.read", "production.deploy"]
    m["denied_tools"] = ["production.deploy"]
    write_manifest(repo, m)
    assert mg.main([]) == 0
    tools = (repo / "control/manifests/_generated/SDE/TOOLS.md").read_text()
    allowed_section = tools.split("## Denied")[0]
    assert "production.deploy" not in allowed_section
    assert "Conflicts resolved (deny wins)" in tools


def test_generation_touches_only_generated_dir(repo):
    """BA-2.4 guard: the generator writes under _generated/ and nowhere else."""
    write_manifest(repo, VALID)
    before = {p for p in repo.rglob("*") if p.is_file()}
    assert mg.main([]) == 0
    after = {p for p in repo.rglob("*") if p.is_file()}
    new = after - before
    gen_root = repo / "control/manifests/_generated"
    assert new and all(gen_root in p.parents for p in new)
