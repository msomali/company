import subprocess
import sys
from pathlib import Path

import frontmatter_lint as fml

REPO = Path(__file__).resolve().parents[3]


def test_extract_none_for_plain_markdown():
    assert fml.extract_front_matter("# Title\nbody\n") is None


def test_extract_returns_yaml_block():
    text = "---\na: 1\nb: two\n---\n# doc\n"
    assert fml.extract_front_matter(text) == "a: 1\nb: two"


def test_extract_unterminated_raises():
    import pytest

    with pytest.raises(ValueError):
        fml.extract_front_matter("---\na: 1\n")


def test_repo_is_clean():
    """The linter must pass on the repository as committed (B1.3 exit bar)."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "control/scripts/frontmatter_lint.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_schema_rejects_bad_status(tmp_path, monkeypatch):
    bad = REPO / "control/adr/ADR-B000-single-bot-identity.md"
    text = bad.read_text().replace("status: APPROVED", "status: BOGUS", 1)
    root = tmp_path
    (root / "control/schemas").mkdir(parents=True)
    (root / "control/schemas/frontmatter.json").write_text(
        (REPO / "control/schemas/frontmatter.json").read_text()
    )
    (root / "control/adr").mkdir()
    (root / "control/adr/bad.md").write_text(text)
    monkeypatch.setattr(fml, "REPO_ROOT", root)
    monkeypatch.setattr(fml, "SCHEMA_PATH", root / "control/schemas/frontmatter.json")
    assert fml.main() == 1


def test_duplicate_artifact_id_detected(tmp_path, monkeypatch):
    fm = "---\nartifact_id: X\ntitle: t\ntype: adr\nproject: control\nowner: o\nversion: '1'\nstatus: APPROVED\nsensitivity: internal\ncreated: 2026-07-16\nupdated: 2026-07-16\n---\n"
    root = tmp_path
    (root / "control/schemas").mkdir(parents=True)
    (root / "control/schemas/frontmatter.json").write_text(
        (REPO / "control/schemas/frontmatter.json").read_text()
    )
    (root / "a.md").write_text(fm)
    (root / "b.md").write_text(fm)
    monkeypatch.setattr(fml, "REPO_ROOT", root)
    monkeypatch.setattr(fml, "SCHEMA_PATH", root / "control/schemas/frontmatter.json")
    assert fml.main() == 1


def test_missing_required_front_matter(tmp_path, monkeypatch):
    root = tmp_path
    (root / "control/schemas").mkdir(parents=True)
    (root / "control/schemas/frontmatter.json").write_text(
        (REPO / "control/schemas/frontmatter.json").read_text()
    )
    (root / "control/adr").mkdir()
    (root / "control/adr/no-fm.md").write_text("# ADR without front matter\n")
    monkeypatch.setattr(fml, "REPO_ROOT", root)
    monkeypatch.setattr(fml, "SCHEMA_PATH", root / "control/schemas/frontmatter.json")
    assert fml.main() == 1
