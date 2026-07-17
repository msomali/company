#!/usr/bin/env python3
"""handoff-check (POL-005, B1.3) — all ten v1 §15 handoff sections non-empty.

Reads the pull-request body from the GitHub Actions event payload
(GITHUB_EVENT_PATH). Fails if any of the ten numbered sections from
.github/pull_request_template.md is missing or has empty content.
HTML comments are stripped before emptiness is judged, so the template's
instructions never count as content.

Exit code 0 = all ten sections present and non-empty; 1 otherwise.
"""
from __future__ import annotations

import json
import os
import re
import sys

SECTIONS = [
    "Requested deliverable",
    "Source requirements and traceability",
    "Assumptions and constraints",
    "Acceptance criteria",
    "Known risks and unresolved questions",
    "Evidence of self-review",
    "Version identifiers",
    "Recommended next action",
    "Next owner",
    "Out of scope",
]


def load_pr_body() -> str:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("FAIL handoff-check: GITHUB_EVENT_PATH not set (not a PR context?)")
        sys.exit(1)
    with open(event_path, encoding="utf-8") as fh:
        event = json.load(fh)
    body = (event.get("pull_request") or {}).get("body")
    return body or ""


def check(body: str) -> list[str]:
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    problems: list[str] = []
    # Split on `## <n>. <title>` headings; tolerate flexible whitespace.
    pattern = re.compile(r"^##\s*(\d+)\.\s*(.+?)\s*$", re.MULTILINE)
    found: dict[int, tuple[str, str]] = {}
    matches = list(pattern.finditer(body))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        found[int(m.group(1))] = (m.group(2), body[start:end].strip())

    for num, title in enumerate(SECTIONS, start=1):
        if num not in found:
            problems.append(f"section {num} ({title}): missing")
            continue
        got_title, content = found[num]
        if got_title.strip().lower() != title.lower():
            problems.append(
                f"section {num}: expected title {title!r}, found {got_title!r}"
            )
        if not content:
            problems.append(f"section {num} ({title}): empty")
    return problems


def main() -> int:
    problems = check(load_pr_body())
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        print(
            f"handoff-check: {len(problems)} problem(s) — every PR must carry the "
            "ten-item handoff package (.github/pull_request_template.md, v1 §15)"
        )
        return 1
    print("handoff-check: all ten handoff sections present and non-empty")
    return 0


if __name__ == "__main__":
    sys.exit(main())
