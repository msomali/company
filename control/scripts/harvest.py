#!/usr/bin/env python3
"""Delivery harvest (ADR-B006) — workspace product -> role task branch.

The dispatcher-side half of the delivery path: collect EXACTLY the envelope's
``required_outputs`` from the role agent's credential-free workspace, refuse
loudly on any defect, and land the product on ``<role>/TASK-###`` with the
constitutional provenance split (author = agenticfoundrybot, the agent-roles
lane; committer = dispatcher, the visible ferry; §80.1/§80.5 as extended by
ADR-B006). The delivery workflow (CI) then validates the agent-authored
handoff and opens the PR as the bot.

Binding implementation requirements (ADR-B006 decision record, 2026-07-22):

1. Every refusal is LOUD and EPISODIC — ``HarvestRefused`` carries the reason,
   and the runtime records a ``harvest_refused`` episode log event before
   re-raising. Never a silent no-op.
2. Pre-push secret scan on the collected set — a hit REFUSES the harvest
   before any commit exists. PR-CI (POL-009) at merge time is too late:
   pushed branch history is already the exposure. Findings name the file and
   pattern, never the matched value.
3. ``required_outputs`` is the COMPLETE delivery manifest: anything not
   listed does not ship (structural output containment — an injected agent
   cannot attach undeclared files to a delivery).

Path contract (v1 §17.4: artifact_id = repo-relative path): each
``required_outputs`` entry is a repo-relative path; the workspace must
contain the SAME relative path. ``handoff.md`` is the standing extra output
(ADR-B006 item 4): read from ``<workspace>/handoff.md``, delivered to
``projects/<PROJECT>/episodes/<TASK>/handoff.md``, and pre-validated with
``handoff_check`` so the episodic refusal fires dispatcher-side, before the
CI backstop.

Custody: no tokens here. Push authentication is the dispatcher clone's
ambient deploy key (core.sshCommand, B4.3 install). Model credentials,
gateway tokens, and the bot PAT never enter this module.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_check  # noqa: E402

BOT_NAME = "agenticfoundrybot"
BOT_EMAIL = "agenticfoundrybot@users.noreply.github.com"
DISPATCHER_NAME = "dispatcher"
DISPATCHER_EMAIL = "dispatcher@company.local"

MAX_FILE_BYTES = 5 * 1024 * 1024  # refuse anything larger; PRs are for review

# High-signal secret patterns (binding requirement 2). Names are printed;
# matched values never are.
SECRET_PATTERNS: dict[str, re.Pattern] = {
    "anthropic-token": re.compile(r"sk-ant-(?:api|oat|ort)[0-9A-Za-z_-]{8,}"),
    "github-classic-pat": re.compile(r"ghp_[0-9A-Za-z]{20,}"),
    "github-fine-grained-pat": re.compile(r"github_pat_[0-9A-Za-z_]{20,}"),
    "aws-access-key-id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}\b"),
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "gateway-token-var": re.compile(r"OPENCLAW_GATEWAY_TOKEN\s*=\s*\S+"),
}


class HarvestError(RuntimeError):
    """Harvest attempted and failed (git/infrastructure defect)."""


class HarvestRefused(HarvestError):
    """Refused before any commit/push existed. Loud by contract: the caller
    records a ``harvest_refused`` episode event with this reason (ADR-B006
    binding requirement 1)."""


@dataclass
class Collected:
    """One file cleared for delivery."""
    rel_path: str          # repo-relative destination
    source: Path           # absolute path inside the workspace
    data: bytes


def _resolve_inside(workspace: Path, rel: str) -> Path:
    """Resolve ``rel`` strictly inside the workspace (no traversal, no
    symlink escape)."""
    if not rel or rel.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", rel):
        raise HarvestRefused(f"required output {rel!r}: absolute paths refused")
    if ".." in Path(rel).parts:
        raise HarvestRefused(f"required output {rel!r}: path traversal refused")
    candidate = (workspace / rel).resolve()
    root = workspace.resolve()
    if not candidate.is_relative_to(root):
        raise HarvestRefused(
            f"required output {rel!r}: escapes the workspace after symlink "
            "resolution; refused"
        )
    return candidate


def collect(workspace: Path, required_outputs: list[str]) -> list[Collected]:
    """Collect exactly the declared outputs. Missing/oversized/escaping
    entries refuse the WHOLE harvest — a partial delivery is a defect, not a
    delivery (required_outputs is the complete manifest)."""
    if not required_outputs:
        raise HarvestRefused(
            "envelope declares no required_outputs — nothing can ship; fix "
            "the envelope (ADR-B006: the field is the delivery manifest)"
        )
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise HarvestRefused(f"workspace {workspace} does not exist/not a dir")
    out: list[Collected] = []
    problems: list[str] = []
    for rel in required_outputs:
        try:
            src = _resolve_inside(workspace, rel)
        except HarvestRefused as exc:
            problems.append(str(exc))
            continue
        if not src.is_file():
            problems.append(f"required output {rel!r}: missing from workspace")
            continue
        data = src.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            problems.append(
                f"required output {rel!r}: {len(data)} bytes exceeds the "
                f"{MAX_FILE_BYTES}-byte delivery cap"
            )
            continue
        out.append(Collected(rel_path=rel, source=src, data=data))
    if problems:
        raise HarvestRefused(
            "incomplete/invalid delivery — " + "; ".join(problems)
        )
    return out


def secret_scan(items: list[Collected]) -> list[str]:
    """Binding requirement 2. Returns findings as 'rel_path: pattern-name'
    strings; NEVER the matched value."""
    findings: list[str] = []
    for item in items:
        try:
            text = item.data.decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001 - binary-safe: scan what decodes
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{item.rel_path}: {name}")
    return findings


def validate_handoff(body: str, head_branch: str) -> list[str]:
    """Dispatcher-side pre-validation (episodic refusal point). The delivery
    workflow re-runs the same authority as the CI backstop."""
    return handoff_check.check(body) + handoff_check.role_claim_problems(
        head_branch, body
    )


def default_git_runner(argv: list[str], cwd: Path, env: dict | None = None):
    """Run git; returns (rc, stdout, stderr)."""
    proc = subprocess.run(
        argv, cwd=str(cwd), env=env, capture_output=True, text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


@dataclass
class GitHarvester:
    """Lands a cleared delivery on ``<role>/TASK-###`` in the dispatcher's
    clone via a temporary worktree — the clone's own checkout (state lane)
    is never disturbed. Injectable runner keeps tests offline."""

    repo_root: Path
    runner: object = field(default=None)
    base_ref: str = "origin/main"
    push: bool = True

    def __post_init__(self):
        self.repo_root = Path(self.repo_root)
        self.runner = self.runner or default_git_runner

    def _git(self, *args: str, cwd: Path | None = None) -> str:
        rc, out, err = self.runner(["git", *args], cwd or self.repo_root)
        if rc != 0:
            raise HarvestError(
                f"git {' '.join(args[:3])}... failed ({rc}): {err.strip()[:300]}"
            )
        return out

    def deliver(
        self,
        *,
        branch: str,
        items: list[Collected],
        handoff_rel: str,
        handoff_body: str,
        task_id: str,
        role: str,
        message: str | None = None,
    ) -> str:
        """Create/refresh ``branch`` from base, write the delivery, commit
        with the ADR-B006 provenance split, push. Returns the commit sha."""
        wt = self.repo_root / ".delivery-worktrees" / branch.replace("/", "-")
        self._git("fetch", "origin", "main")
        if wt.exists():
            self._git("worktree", "remove", "--force", str(wt))
        # Reuse the branch if it exists (revision cycles append); else create
        # from base so state-lane history never leaks into the delivery lane.
        rc, _, _ = self.runner(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            self.repo_root,
        )
        if rc == 0:
            self._git("worktree", "add", str(wt), branch)
        else:
            self._git("worktree", "add", "-b", branch, str(wt), self.base_ref)
        try:
            for item in items:
                dest = wt / item.rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(item.data)
            handoff_dest = wt / handoff_rel
            handoff_dest.parent.mkdir(parents=True, exist_ok=True)
            handoff_dest.write_text(handoff_body, encoding="utf-8")
            rels = [i.rel_path for i in items] + [handoff_rel]
            self._git("add", "--", *rels, cwd=wt)
            msg = message or (
                f"{task_id} ({role}): delivery — {len(rels)} artifact(s)\n\n"
                f"Task: {task_id}\nRole: {role}\n"
                "Delivered-by: dispatcher harvest (ADR-B006)"
            )
            self._git(
                "-c", f"user.name={DISPATCHER_NAME}",
                "-c", f"user.email={DISPATCHER_EMAIL}",
                "commit",
                f"--author={BOT_NAME} <{BOT_EMAIL}>",
                "-m", msg,
                cwd=wt,
            )
            sha = self._git("rev-parse", "HEAD", cwd=wt).strip()
            if self.push:
                self._git("push", "-u", "origin", branch, cwd=wt)
            return sha
        finally:
            self.runner(
                ["git", "worktree", "remove", "--force", str(wt)],
                self.repo_root,
            )


def run_harvest(
    *,
    repo_root: Path,
    workspace: Path,
    project_id: str,
    task_id: str,
    role: str,
    required_outputs: list[str],
    slug: str | None = None,
    harvester: GitHarvester | None = None,
) -> dict:
    """Full harvest pipeline: collect -> secret-scan -> handoff pre-check ->
    branch/commit/push. Raises HarvestRefused (episodic, binding req 1) on
    any content defect; HarvestError on infrastructure failure. Returns
    {branch, sha, files} on success."""
    role_lc = role.lower()
    branch = f"{role_lc}/{task_id}" + (f"-{slug}" if slug else "")

    items = collect(workspace, required_outputs)

    findings = secret_scan(items)
    if findings:
        raise HarvestRefused(
            "secret scan hit — delivery refused BEFORE any commit/push "
            "(ADR-B006 binding requirement 2): " + "; ".join(findings)
        )

    handoff_src = Path(workspace) / "handoff.md"
    if not handoff_src.is_file():
        raise HarvestRefused(
            "workspace has no handoff.md — the agent-authored §15 ten-section "
            "handoff is a standing required output (ADR-B006 item 4)"
        )
    handoff_body = handoff_src.read_text(encoding="utf-8")
    problems = validate_handoff(handoff_body, branch)
    if problems:
        raise HarvestRefused(
            "handoff.md fails handoff_check (dispatcher-side pre-validation; "
            "CI is the backstop, not the first gate): " + "; ".join(problems)
        )
    if secret_scan([Collected("handoff.md", handoff_src,
                              handoff_body.encode("utf-8"))]):
        raise HarvestRefused("secret scan hit in handoff.md — delivery refused")

    handoff_rel = f"projects/{project_id}/episodes/{task_id}/handoff.md"
    harvester = harvester or GitHarvester(repo_root=repo_root)
    sha = harvester.deliver(
        branch=branch,
        items=items,
        handoff_rel=handoff_rel,
        handoff_body=handoff_body,
        task_id=task_id,
        role=role,
    )
    return {
        "branch": branch,
        "sha": sha,
        "files": [i.rel_path for i in items] + [handoff_rel],
    }
