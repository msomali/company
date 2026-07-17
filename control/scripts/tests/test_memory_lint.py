"""Tests for memory_lint.py (B6.1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import memory_lint as ml  # noqa: E402

VALIDATOR = Draft7Validator(
    json.loads((SCRIPTS.parents[1] / "control" / "schemas" / "memory.json").read_text())
)

FM = """\
---
memory_id: MEM-SDE-0001
namespace: roles/sde
type: observed
subject: sample subject line
source: "PR #1"
creator: sde agent
confidence: high
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
retention: review at §87
---

Body content.
"""


def write(tmp_path: Path, rel: str, text: str) -> tuple[Path, str]:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, rel


def test_valid_record_clean(tmp_path):
    path, rel = write(tmp_path, "memory/roles/sde/MEM-SDE-0001.md", FM)
    fm, problems = ml.lint_file(path, rel, VALIDATOR)
    assert problems == []
    assert fm["memory_id"] == "MEM-SDE-0001"


def test_missing_type_fails(tmp_path):
    bad = FM.replace("type: observed\n", "")
    path, rel = write(tmp_path, "memory/roles/sde/MEM-SDE-0001.md", bad)
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert any("'type' is a required property" in p for p in problems)


def test_namespace_path_mismatch_fails(tmp_path):
    path, rel = write(tmp_path, "memory/org/MEM-SDE-0001.md", FM)
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert any("does not match path namespace" in p for p in problems)


def test_filename_id_mismatch_fails(tmp_path):
    path, rel = write(tmp_path, "memory/roles/sde/MEM-SDE-9999.md", FM)
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert any("!= memory_id" in p for p in problems)


def test_tombstone_with_content_fails(tmp_path):
    tomb = FM.replace(
        "retention: review at §87\n",
        "retention: review at §87\ntombstone: true\npurged_at: \"2026-07-17\"\npurge_reason: superseded and purged\n",
    ).replace("Body content.\n", "Tombstone.\n\nline2\nline3\nline4\n")
    path, rel = write(tmp_path, "memory/roles/sde/MEM-SDE-0001.md", tomb)
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert any("tombstone retains content" in p for p in problems)


def test_tombstone_without_purge_fields_fails(tmp_path):
    tomb = FM.replace(
        "retention: review at §87\n", "retention: review at §87\ntombstone: true\n"
    ).replace("Body content.\n", "Tombstone.\n")
    path, rel = write(tmp_path, "memory/roles/sde/MEM-SDE-0001.md", tomb)
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert any("purged_at" in p for p in problems)


def test_no_front_matter_fails(tmp_path):
    path, rel = write(tmp_path, "memory/org/MEM-ORG-0009.md", "just prose\n")
    _, problems = ml.lint_file(path, rel, VALIDATOR)
    assert problems == ["memory record missing front matter"]


def test_repo_tree_clean():
    """The committed /memory tree (incl. seed MEM-ORG-0001) lints clean."""
    assert ml.main() == 0
