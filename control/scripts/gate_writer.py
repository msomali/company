#!/usr/bin/env python3
"""gate-writer (v2 §78 row 4, B5.2) — emit gates/GATE-*.yaml on merge.

Trigger: pull_request closed event with merged == true (see
.github/workflows/gate-writer.yml). Reads the event payload, fetches the PR's
reviews, and builds a Gate Decision Record (v2 §8) validated against
control/schemas/gate.json.

Write path: `main` requires a PR for every identity (v2 §79 as applied in
branch protection), so CI cannot push gate records directly. The writer
therefore commits the record to a `gate/pr-<N>` branch and opens a PR with
the bot token (GH_TOKEN_AGENTICFOUNDRYBOT — SECRETS-MANIFEST); the human
owner merges it like everything else. Gate PRs themselves are skipped by the
workflow guard (head `gate/*`), so record-keeping does not recurse.

Role attribution (§86-C6): the record carries the *claimed* role parsed from
approving review bodies (`role: SAT` line or `GATE-SAT` marker). Absent any
claim, the gate owner is HUMAN — the required owner review is the decision.

Modes:
  (CI)            gate_writer.py                    — full run: write, push, PR
  gate_writer.py --dry-run                          — build + validate + write only
  gate_writer.py --event <path> [--reviews <path>]  — offline inputs (tests)
  gate_writer.py --pr <N> / workflow_dispatch pr_number — replay: fetch an
                  already-merged PR from the API when its merge event was
                  consumed (e.g. by a failed run)

Exit 0 on success or benign skip (unmerged close, gate/ head, no event in a
manual dispatch); exit 1 on real failure (invalid record, push/PR error).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCHEMA = REPO_ROOT / "control" / "schemas" / "gate.json"
GATES_DIR = REPO_ROOT / "gates"
ROLES = ("SAT", "SSE", "DPC", "DCE", "PJM")  # HUMAN is the fallback, not a claim
CRITERIA_VERSION = "v2§8/v1§15 handoff rev 1"
BOT_NAME = "agenticfoundrybot"
BOT_EMAIL = "agenticfoundrybot@users.noreply.github.com"


def gh_api(path: str, token: str) -> object:
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    req = urllib.request.Request(
        f"{api}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "company-gate-writer",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def claimed_role(texts: list[str]) -> str:
    """§86-C6: first explicit role claim wins; no claim → HUMAN."""
    for text in texts:
        for role in ROLES:
            if re.search(
                rf"(?im)^role:\s*{role}\b|\bGATE-{role}\b", text or ""
            ):
                return role
    return "HUMAN"


def section(body: str, num: int) -> str:
    """Extract handoff section <num> content from a PR body."""
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.DOTALL)
    matches = list(re.finditer(r"^##\s*(\d+)\.\s*.+?\s*$", body, re.MULTILINE))
    for i, m in enumerate(matches):
        if int(m.group(1)) == num:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            return body[m.end() : end].strip()
    return ""


def build_gate_record(pr: dict, reviews: list[dict]) -> dict:
    approvals = [r for r in reviews if r.get("state") == "APPROVED"]
    review_texts = [r.get("body") or "" for r in approvals]
    owner = claimed_role(review_texts + [pr.get("body") or ""])
    sha = (pr.get("merge_commit_sha") or "")[:8] or "unknown"
    number = pr["number"]

    evidence = [pr.get("html_url") or f"PR #{number}"]
    evidence += [r["html_url"] for r in approvals if r.get("html_url")]
    evidence.append(f"merge:{pr.get('merge_commit_sha') or 'unknown'}")

    findings = [
        line.strip()
        for text in review_texts
        for line in text.splitlines()
        if line.strip().startswith(("Nit", "Finding", "- "))
    ][:10]

    next_owner = section(pr.get("body") or "", 9).splitlines()
    record = {
        "gate_id": f"GATE-{owner}-PR{number}-{sha}",
        "artifact_or_release": f"PR #{number}: {(pr.get('title') or '').strip()}",
        "gate_owner": owner,
        "decision": "APPROVED",  # the merge itself is the decision event
        "criteria_version": CRITERIA_VERSION,
        "evidence": evidence,
        "findings": findings,
        "conditions": [],
        "expires": None,
        "next_owner": (next_owner[0].strip() if next_owner else "human owner"),
        "decided_at": pr.get("merged_at") or "unknown",
        "approval_message_ref": (
            approvals[-1]["html_url"] if approvals and approvals[-1].get("html_url") else None
        ),
    }
    validator = Draft7Validator(json.loads(GATE_SCHEMA.read_text(encoding="utf-8")))
    errors = sorted(validator.iter_errors(record), key=str)
    if errors:
        raise ValueError("; ".join(e.message for e in errors))
    return record


def gate_pr_body(record: dict, pr_number: int) -> str:
    gid = record["gate_id"]
    return "\n".join(
        f"## {i}. {title}\n{content}\n"
        for i, (title, content) in enumerate(
            [
                ("Requested deliverable", f"Gate decision record `{gid}` for merged PR #{pr_number} (v2 §78 row 4)."),
                ("Source requirements and traceability", "v2 §8 (record format); §86-C6 (claimed-role attribution); §88 check 7; B5.2."),
                ("Assumptions and constraints", "Generated by gate-writer CI from the merge event and review data; main requires a PR for every identity, so the record lands by PR instead of direct CI push."),
                ("Acceptance criteria", "Record validates against control/schemas/gate.json; evidence links resolve to the PR, its approving reviews, and the merge commit."),
                ("Known risks and unresolved questions", "Role attribution is claimed, not proven (§86-C6) — the human owner verifies attribution at this merge."),
                ("Evidence of self-review", "Schema validation ran in the emitting workflow; a failing record aborts before any branch is pushed."),
                ("Version identifiers", f"criteria_version: {record['criteria_version']}; decided_at: {record['decided_at']}."),
                ("Recommended next action", "Owner merges to place the record under gates/ on main."),
                ("Next owner", "Human owner (merge)."),
                ("Out of scope", "Any change outside gates/; gate records for gate PRs (guarded against recursion)."),
            ],
            start=1,
        )
    )


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(REPO_ROOT), *args], check=True)


def publish(record: dict, gate_path: Path, pr_number: int, token: str) -> None:
    branch = f"gate/pr-{pr_number}"
    rel = gate_path.relative_to(REPO_ROOT)
    git("checkout", "-B", branch)
    git("add", str(rel))
    git(
        "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
        "commit", "-m", f"gate: {record['gate_id']} (auto, B5.2)",
    )
    repo = os.environ.get("GITHUB_REPOSITORY", "msomali/company")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    remote = f"{server}/{repo}.git".replace(
        "https://", f"https://x-access-token:{token}@", 1
    )
    git("push", "--force-with-lease", remote, f"HEAD:refs/heads/{branch}")
    body = gate_pr_body(record, pr_number)
    subprocess.run(
        [
            "gh", "pr", "create",
            "--repo", repo,
            "--base", "main",
            "--head", branch,
            "--title", f"gate: {record['gate_id']}",
            "--body", body,
        ],
        check=True,
        env={**os.environ, "GH_TOKEN": token},
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gate-writer (v2 §78 row 4)")
    ap.add_argument("--event", help="event payload JSON (default: $GITHUB_EVENT_PATH)")
    ap.add_argument("--pr", help="replay: PR number to fetch from the API")
    ap.add_argument("--reviews", help="reviews JSON file (offline/testing)")
    ap.add_argument("--dry-run", action="store_true", help="write record only")
    ap.add_argument("--out-dir", help="output dir (default: gates/)")
    args = ap.parse_args(argv)

    event_path = args.event or os.environ.get("GITHUB_EVENT_PATH")
    event = {}
    if event_path and Path(event_path).is_file():
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = event.get("pull_request")
    if not pr:
        number = str(
            args.pr or (event.get("inputs") or {}).get("pr_number") or ""
        ).strip()
        if not number:
            print("gate-writer: no PR event and no pr_number — nothing to do")
            return 0
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        repo = os.environ.get("GITHUB_REPOSITORY", "msomali/company")
        try:
            pr = gh_api(f"/repos/{repo}/pulls/{int(number)}", token)
        except Exception as exc:  # noqa: BLE001 — replay is operator-driven
            print(f"gate-writer: replay fetch of PR {number} failed: {exc}", file=sys.stderr)
            return 1
        print(f"gate-writer: replaying merged PR #{number}")
    if not pr.get("merged"):
        print("gate-writer: PR closed without merge — no gate record")
        return 0
    head_ref = (pr.get("head") or {}).get("ref", "")
    if head_ref.startswith("gate/"):
        print("gate-writer: gate PR merged — recursion guard, no record")
        return 0

    if args.reviews:
        reviews = json.loads(Path(args.reviews).read_text(encoding="utf-8"))
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not token:
            print("gate-writer: no token for review fetch", file=sys.stderr)
            return 1
        repo = os.environ.get("GITHUB_REPOSITORY", "msomali/company")
        reviews = gh_api(f"/repos/{repo}/pulls/{pr['number']}/reviews", token)

    try:
        record = build_gate_record(pr, reviews)
    except ValueError as exc:
        print(f"gate-writer: record failed schema validation: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir) if args.out_dir else GATES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_path = out_dir / f"{record['gate_id']}.yaml"
    gate_path.write_text(
        "# Gate Decision Record (v2 §8) — emitted by gate-writer (B5.2)\n"
        + yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"gate-writer: wrote {gate_path}")
    if args.dry_run or args.out_dir:
        return 0

    token = os.environ.get("GH_TOKEN") or ""
    if not token:
        print("gate-writer: no GH_TOKEN to publish", file=sys.stderr)
        return 1
    try:
        publish(record, gate_path, pr["number"], token)
    except subprocess.CalledProcessError as exc:
        print(f"gate-writer: publish failed: {exc}", file=sys.stderr)
        return 1
    print(f"gate-writer: opened gate PR from gate/pr-{pr['number']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
