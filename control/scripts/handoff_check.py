#!/usr/bin/env python3
"""handoff-check (POL-005, B1.3) — all ten v1 §15 handoff sections non-empty.

Reads the pull-request body from the GitHub Actions event payload
(GITHUB_EVENT_PATH). Fails if any of the ten numbered sections from
.github/pull_request_template.md is missing or has empty content.
HTML comments are stripped before emptiness is judged, so the template's
instructions never count as content.

Additionally (§86-C6 claim-channel rule, 2026-07-18, MEM-ORG-0004): a PR
whose head branch carries a role prefix (sde/, sat/, ...) MUST state its
gate role machine-readably in the body — a line beginning `role: <ROLE>`.
Rationale: under ADR-B000 the author-bot cannot review its own PR, so the
approving-review-body claim channel is structurally dead for every bot-role
PR; the PR body is the only live channel gate-writer can parse. A doctrine
rule with no gate silently regresses — hence this check.

Exit code 0 = clean; 1 otherwise.
"""
from __future__ import annotations

import json
import os
import re
import sys

# All thirteen role short-codes (ADR-B001) — branch prefixes that mark a PR
# as bot-role work.
ROLE_BRANCH_PREFIXES = (
    "pjm", "saa", "uud", "sde", "sat", "sse", "dpc",
    "dce", "de", "aie", "tw", "ale", "lin",
)
# Roles a body claim may name: the five gate-owner roles (gate.json enum)
# plus explicit HUMAN (a conscious "no bot-role gate on this PR" claim;
# gate-writer treats it as the fallback it would apply anyway).
CLAIMABLE = ("SAT", "SSE", "DPC", "DCE", "PJM", "HUMAN")
CLAIM_RE = re.compile(
    r"(?im)^role:\s*(" + "|".join(CLAIMABLE) + r")\b"
)

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


def load_pr() -> tuple[str, str]:
    """Return (body, head_ref) from the Actions event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("FAIL handoff-check: GITHUB_EVENT_PATH not set (not a PR context?)")
        sys.exit(1)
    with open(event_path, encoding="utf-8") as fh:
        event = json.load(fh)
    pr = event.get("pull_request") or {}
    return pr.get("body") or "", ((pr.get("head") or {}).get("ref") or "")


def role_claim_problems(head_ref: str, body: str) -> list[str]:
    """§86-C6 claim-channel rule: role-prefixed branch → body must claim a
    gate role. Comments are stripped so template guidance can never satisfy
    (or fake) the claim."""
    prefix = head_ref.split("/", 1)[0].lower() if "/" in head_ref else ""
    if prefix not in ROLE_BRANCH_PREFIXES:
        return []
    stripped = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    if CLAIM_RE.search(stripped):
        return []
    return [
        f"role claim: branch {head_ref!r} is bot-role work ({prefix}/) but the "
        "PR body has no machine-readable gate-role claim — add a line "
        "beginning with the word 'role:' followed by one of "
        f"{', '.join(CLAIMABLE)}. Under ADR-B000 the author-bot cannot review "
        "its own PR, so the PR body is the only claim channel gate-writer can "
        "parse (§86-C6, MEM-ORG-0004)"
    ]


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
    body, head_ref = load_pr()
    problems = check(body) + role_claim_problems(head_ref, body)
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
