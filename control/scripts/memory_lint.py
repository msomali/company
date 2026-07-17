#!/usr/bin/env python3
"""memory-lint (B6.1) — validate /memory tree records, v2.1 §83 / v2 §28.

Rules:
  1. Every tracked memory/**/*.md except README.md carries §28 front matter
     valid against control/schemas/memory.json (type field mandatory, §83.2).
  2. memory_id is unique and matches the filename (<memory_id>.md).
  3. namespace matches the record's path (org ↔ memory/org/,
     roles/<r> ↔ memory/roles/<r>/).
  4. Tombstones (tombstone: true) keep no content: body must be only the
     tombstone notice (≤ 3 non-empty lines) — provenance-preserving
     redaction per v2 §31.
  5. Supersession links must point at existing memory_ids
     (superseded_by may dangle only if the successor is in the same change).

Exit 0 = clean; 1 = violations (printed as `path: message`).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "control" / "schemas" / "memory.json"
MEMORY_DIR = "memory"


def tracked_memory_files(root: Path) -> list[tuple[Path, str]]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", f"{MEMORY_DIR}/**/*.md", f"{MEMORY_DIR}/*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        (root / rel, rel)
        for rel in sorted(set(out.splitlines()))
        if rel and Path(rel).name != "README.md"
    ]


def split_front_matter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated front-matter fence")
    return text[4:end], text[end + 4 :]


def lint_file(path: Path, rel: str, validator: Draft7Validator) -> tuple[dict | None, list[str]]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm_text, body = split_front_matter(text)
    except ValueError as exc:
        return None, [str(exc)]
    if fm_text is None:
        return None, ["memory record missing front matter"]
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        return None, [f"front matter unparseable: {exc}"]
    if not isinstance(fm, dict):
        return None, ["front matter is not a mapping"]

    for err in sorted(validator.iter_errors(fm), key=str):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        problems.append(f"front matter invalid at {loc}: {err.message}")

    mid = fm.get("memory_id", "")
    if mid and Path(rel).stem != mid:
        problems.append(f"filename {Path(rel).name!r} != memory_id {mid!r}")

    ns = fm.get("namespace", "")
    parts = Path(rel).parts  # ('memory', 'org', 'MEM-ORG-0001.md') etc.
    path_ns = "/".join(parts[1:-1])
    if ns and path_ns and ns != path_ns:
        problems.append(f"namespace {ns!r} does not match path namespace {path_ns!r}")

    if fm.get("tombstone") is True:
        content_lines = [ln for ln in body.splitlines() if ln.strip()]
        if len(content_lines) > 3:
            problems.append(
                f"tombstone retains content ({len(content_lines)} non-empty lines; max 3)"
            )
    return fm, problems


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]) if argv else REPO_ROOT
    validator = Draft7Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    files = tracked_memory_files(root)
    failures = 0
    seen: dict[str, str] = {}
    all_ids: set[str] = set()
    links: list[tuple[str, str, str]] = []

    records = []
    for path, rel in files:
        fm, problems = lint_file(path, rel, validator)
        records.append((rel, fm))
        if fm:
            mid = fm.get("memory_id", "")
            if mid in seen:
                problems.append(f"duplicate memory_id {mid!r} (also {seen[mid]})")
            elif mid:
                seen[mid] = rel
                all_ids.add(mid)
            for field in ("supersedes", "superseded_by"):
                if fm.get(field):
                    links.append((rel, field, fm[field]))
        for msg in problems:
            print(f"{rel}: {msg}")
            failures += 1

    for rel, field, target in links:
        if target not in all_ids:
            print(f"{rel}: {field} points at unknown memory_id {target!r}")
            failures += 1

    if failures:
        print(f"memory-lint: {failures} problem(s)")
        return 1
    print(f"memory-lint: clean ({len(files)} record(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
