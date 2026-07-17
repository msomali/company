"""Tests for memory_purge.py (B6.1) — against throwaway git repos."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import memory_purge as mp  # noqa: E402

TOMB = """\
---
memory_id: MEM-ORG-0002
namespace: org
type: observed
subject: tombstoned record
source: "PR #2"
creator: bootstrap
confidence: high
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
retention: n/a (purged)
tombstone: true
purged_at: "2026-07-17"
purge_reason: test purge
---

Tombstone.
"""

LIVE = TOMB.replace("tombstone: true\npurged_at: \"2026-07-17\"\npurge_reason: test purge\n", "")


def repo(tmp_path: Path, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return tmp_path


def test_purge_tombstone_clean(tmp_path):
    root = repo(tmp_path, {"memory/org/MEM-ORG-0002.md": TOMB})
    assert mp.main(["--id", "MEM-ORG-0002", "--root", str(root)]) == 0


def test_live_record_refuses_purge(tmp_path):
    root = repo(tmp_path, {"memory/org/MEM-ORG-0002.md": LIVE})
    assert mp.main(["--id", "MEM-ORG-0002", "--root", str(root)]) == 1


def test_missing_record_fails(tmp_path):
    root = repo(tmp_path, {"memory/org/MEM-ORG-0002.md": TOMB})
    assert mp.main(["--id", "MEM-ORG-0404", "--root", str(root)]) == 1


def test_residue_detected(tmp_path):
    other = LIVE.replace("MEM-ORG-0002", "MEM-ORG-0003").replace(
        "Tombstone.", "See MEM-ORG-0002 for details."
    )
    root = repo(
        tmp_path,
        {"memory/org/MEM-ORG-0002.md": TOMB, "memory/org/MEM-ORG-0003.md": other},
    )
    assert mp.main(["--id", "MEM-ORG-0002", "--root", str(root)]) == 1


def test_supersession_link_is_allowed_residue(tmp_path):
    # a front-matter supersession line is provenance, not live residue (v2 §31)
    other = LIVE.replace("MEM-ORG-0002", "MEM-ORG-0003").replace(
        'source: "PR #2"', 'source: "PR #2"\nsupersedes: MEM-ORG-0002'
    )
    root = repo(
        tmp_path,
        {"memory/org/MEM-ORG-0002.md": TOMB, "memory/org/MEM-ORG-0003.md": other},
    )
    assert mp.main(["--id", "MEM-ORG-0002", "--root", str(root)]) == 0


def test_index_purge_removes_entries(tmp_path):
    root = repo(tmp_path, {"memory/org/MEM-ORG-0002.md": TOMB})
    index = root / "memory" / ".index"
    index.mkdir(parents=True)
    (index / "hit.txt").write_text("MEM-ORG-0002 -> vector 123")
    (index / "miss.txt").write_text("MEM-ORG-9999 -> vector 456")
    assert mp.main(["--id", "MEM-ORG-0002", "--root", str(root)]) == 0
    assert not (index / "hit.txt").exists()
    assert (index / "miss.txt").exists()
