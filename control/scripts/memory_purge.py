#!/usr/bin/env python3
"""memory-purge (B6.1) — index purge + residue check for forgotten records,
v2.1 §83.4 / v2 §31.

Deletion flow: a PR replaces the record's content with tombstone front matter
(tombstone: true, purged_at, purge_reason — memory-lint enforces the shape),
then this script runs:

  memory_purge.py --id MEM-ORG-0001 [--root <repo>]

Actions:
  1. Verify the record file exists and is a tombstone.
  2. Purge derived indexes: remove any files under memory/.index/ that
     mention the memory_id (the directory is the §83 slot for future
     retrieval indexes; absent during bootstrap → step reports SKIP).
  3. Residue check: no other tracked file under memory/ may reference the
     purged memory_id, except via supersedes/superseded_by provenance links
     (provenance-preserving redaction, v2 §31) or its own tombstone.

Exit 0 = purged and clean; 1 = failure (not a tombstone, or live residue).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR_NAME = ".index"


def tracked_memory_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "memory/**", "memory/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(set(ln for ln in out.splitlines() if ln))


def find_record(root: Path, memory_id: str) -> Path | None:
    hits = [p for p in (root / "memory").rglob(f"{memory_id}.md") if p.is_file()]
    return hits[0] if hits else None


def is_tombstone(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    try:
        fm = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return False
    return isinstance(fm, dict) and fm.get("tombstone") is True


def purge_index(root: Path, memory_id: str) -> list[str]:
    index_dir = root / "memory" / INDEX_DIR_NAME
    removed: list[str] = []
    if not index_dir.is_dir():
        return removed
    for path in sorted(index_dir.rglob("*")):
        if path.is_file() and memory_id in path.read_text(
            encoding="utf-8", errors="replace"
        ):
            path.unlink()
            removed.append(str(path.relative_to(root)))
    return removed


def residue_check(root: Path, memory_id: str, record_rel: str) -> list[str]:
    residue: list[str] = []
    pattern = re.compile(re.escape(memory_id))
    for rel in tracked_memory_files(root):
        if rel == record_rel or INDEX_DIR_NAME in Path(rel).parts:
            continue
        path = root / rel
        if not path.is_file():
            continue
        for i, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if pattern.search(line) and not re.match(
                r"\s*(supersedes|superseded_by)\s*:", line
            ):
                residue.append(f"{rel}:{i}: {line.strip()[:80]}")
    return residue


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Memory purge (v2.1 §83.4)")
    ap.add_argument("--id", required=True, help="memory_id to purge")
    ap.add_argument("--root", help="repo root (testing)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else REPO_ROOT

    record = find_record(root, args.id)
    if record is None:
        print(f"memory-purge: no record file for {args.id}", file=sys.stderr)
        return 1
    if not is_tombstone(record):
        print(
            f"memory-purge: {record} is not a tombstone — replace its content "
            "with tombstone front matter first (reviewed PR)",
            file=sys.stderr,
        )
        return 1

    removed = purge_index(root, args.id)
    if removed:
        for rel in removed:
            print(f"purged index entry: {rel}")
    else:
        print("index purge: SKIP (no derived index present)")

    record_rel = str(record.relative_to(root))
    residue = residue_check(root, args.id, record_rel)
    if residue:
        print(f"memory-purge: live residue for {args.id}:", file=sys.stderr)
        for line in residue:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"memory-purge: {args.id} purged; no live residue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
