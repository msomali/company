#!/usr/bin/env python3
"""frontmatter-lint (POL-004, B1.3) — validate artifact front matter.

Rules:
  1. Any tracked *.md file that begins with a `---` YAML front-matter fence
     must contain valid YAML that validates against
     control/schemas/frontmatter.json.
  2. Files under REQUIRED_FM_DIRS (except README.md) MUST carry front matter.
  3. `artifact_id` values must be unique across the repository.

Exit code 0 = clean; 1 = violations (each printed as `path: message`).
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "control" / "schemas" / "frontmatter.json"

# Directories whose Markdown artifacts must carry front matter (v1.1 §52.3).
REQUIRED_FM_DIRS = ("control/adr", "control/escalations")

# Trees never linted: canonical handoff docs, git internals, and the /memory
# tree — memory records carry §28 front matter validated by memory_lint.py
# against control/schemas/memory.json (B6.1), not the artifact schema.
EXCLUDED_TOP_LEVEL = (".git", "handoff", "memory")


def iter_markdown_files(root: Path):
    """Yield git-tracked *.md files (fallback: rglob) minus excluded trees."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "*.md"],
            capture_output=True, text=True, check=True,
        ).stdout
        rels = sorted(line for line in out.splitlines() if line)
    except (OSError, subprocess.CalledProcessError):
        rels = sorted(
            str(p.relative_to(root)) for p in root.rglob("*.md")
        )
    for rel in rels:
        if rel.split("/", 1)[0] in EXCLUDED_TOP_LEVEL:
            continue
        yield root / rel, rel


def extract_front_matter(text: str):
    """Return (yaml_str or None). Front matter = leading `---` fenced block."""
    if not text.startswith("---\n") and text != "---":
        return None
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated front-matter fence")
    return text[4:end]


def normalize_dates(data: dict) -> dict:
    """YAML 1.1 loads bare dates as date objects; on disk they are strings.
    Normalize so the schema's `type: string` judges file content, not
    loader coercion. Mutates and returns ``data``."""
    for key, value in list(data.items()):
        if isinstance(value, (datetime.date, datetime.datetime)):
            data[key] = value.isoformat()
    return data


_VALIDATOR = None


def schema_problems(data: dict) -> list[str]:
    """Schema violations for one front-matter mapping, as `where: message`
    strings. Single authority shared by main() here and the ADR-B006
    harvest pre-validation (control/scripts/harvest.py) — the two judging
    the same head differently is exactly the drift the 2026-07-23 delivery
    cycle exposed."""
    global _VALIDATOR
    if _VALIDATOR is None:
        _VALIDATOR = Draft7Validator(json.loads(SCHEMA_PATH.read_text()))
    normalize_dates(data)
    return [
        ("/".join(str(p) for p in err.absolute_path) or "(root)")
        + f": {err.message}"
        for err in sorted(_VALIDATOR.iter_errors(data), key=str)
    ]


def main() -> int:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}

    for path, rel in iter_markdown_files(REPO_ROOT):
        text = path.read_text(encoding="utf-8")
        try:
            fm_text = extract_front_matter(text)
        except ValueError as exc:
            errors.append(f"{rel}: {exc}")
            continue

        required = rel.startswith(tuple(d + "/" for d in REQUIRED_FM_DIRS)) and (
            path.name != "README.md"
        )
        if fm_text is None:
            if required:
                errors.append(f"{rel}: front matter required in this directory")
            continue

        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: front matter is not valid YAML ({exc})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: front matter must be a YAML mapping")
            continue

        for problem in schema_problems(data):
            errors.append(f"{rel}: {problem}")

        artifact_id = data.get("artifact_id")
        if isinstance(artifact_id, str):
            if artifact_id in seen_ids:
                errors.append(
                    f"{rel}: duplicate artifact_id {artifact_id!r} "
                    f"(also in {seen_ids[artifact_id]})"
                )
            else:
                seen_ids[artifact_id] = rel

    for line in errors:
        print(f"FAIL {line}")
    if errors:
        print(f"frontmatter-lint: {len(errors)} violation(s)")
        return 1
    print(f"frontmatter-lint: clean ({len(seen_ids)} artifact(s) validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
