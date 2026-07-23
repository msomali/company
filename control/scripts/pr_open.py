#!/usr/bin/env python3
"""pr-open — the only sanctioned PR-creation path for bootstrap (2026-07-22).

Validates the PR body through handoff_check BEFORE any network call and
REFUSES to create the pull request on any failure: loud FAIL lines, non-zero
exit, nothing opened. Validation needs no token and touches no network — the
refusal path is structurally offline. Only a fully green body reaches the
GitHub REST call.

Why this exists: four PR-body defects (#84 ... #98, two total omissions)
proved that a remembered pre-open check does not survive session boundaries.
Habits that fail repeatedly get replaced by structure — same rule as the
seat-check and the auth probe. Bootstrap opens PRs exclusively through this
helper (TOOLS.md); `gh pr create` / raw REST are no longer paths that exist.

Usage:
    python3 control/scripts/pr_open.py \
        --title "..." --body-file body.md --head my/branch [--base main] \
        [--repo msomali/company] [--token-file .secrets/gh-token]

Exit codes: 0 created; 2 body refused (nothing opened); 3 GitHub API error.
The token is read only after validation passes, from the GH_TOKEN
environment variable or --token-file, and is never printed (BA-2.2 /
ADR-B002).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_check  # noqa: E402  (same-directory import by design)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO = "msomali/company"
DEFAULT_TOKEN_FILE = REPO_ROOT / ".secrets" / "gh-token"
API = "https://api.github.com"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pr_open",
        description="Create a GitHub PR only if the body passes handoff_check.",
    )
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True, help="File containing the PR body")
    p.add_argument("--head", required=True, help="Head branch name")
    p.add_argument("--base", default="main")
    p.add_argument("--repo", default=DEFAULT_REPO, help="owner/name")
    p.add_argument(
        "--ok-if-exists",
        action="store_true",
        help="Exit 0 when GitHub reports a PR already open for this head "
        "(delivery re-pushes update the existing PR)",
    )
    p.add_argument(
        "--token-file",
        default=str(DEFAULT_TOKEN_FILE),
        help="Read the GitHub token here when the GH_TOKEN env var is unset "
        "(read only after validation passes; never printed)",
    )
    return p


def validate_body(body: str, head: str) -> list[str]:
    """Full parity with CI: ten sections plus the §86-C6 role-claim rule."""
    return handoff_check.check(body) + handoff_check.role_claim_problems(head, body)


def load_token(token_file: str) -> str:
    token = os.environ.get("GH_TOKEN", "").strip()
    if token:
        return token
    token = Path(token_file).read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"empty token file: {token_file}")
    return token


def create_pr(*, repo: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{API}/repos/{repo}/pulls",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "agenticfoundrybot",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main(argv: list[str] | None = None, create=create_pr) -> int:
    args = build_parser().parse_args(argv)
    body = Path(args.body_file).read_text(encoding="utf-8")

    problems = validate_body(body, args.head)
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"pr_open: REFUSED — {len(problems)} handoff problem(s); "
            "no pull request was created. Fix the body file and re-run.",
            file=sys.stderr,
        )
        return 2

    try:
        token = load_token(args.token_file)
    except (OSError, ValueError) as exc:
        print(f"pr_open: token unavailable ({exc}); nothing opened.", file=sys.stderr)
        return 3

    payload = {
        "title": args.title,
        "body": body,
        "head": args.head,
        "base": args.base,
    }
    try:
        result = create(repo=args.repo, token=token, payload=payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        if args.ok_if_exists and exc.code == 422 and "already exists" in detail:
            print(f"EXISTS — a pull request is already open for {args.head}; "
                  "the push updated it. Nothing to create.")
            return 0
        print(f"pr_open: GitHub API error {exc.code}; nothing opened.\n{detail}",
              file=sys.stderr)
        return 3

    print(f"OPENED {result.get('html_url', '<no url in response>')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
