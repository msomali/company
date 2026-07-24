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

Delivery-cycle findings (owner, 2026-07-23): unreadable inputs REFUSE
instead of crashing (finding 3 — the req-1 gap), the handoff's §14 front
matter is STAMPED mechanically from envelope + clock (finding 6 — schema
drift closed by construction; envelopes stop teaching the schema), and
delivered ``*.md`` heads are pre-validated with the frontmatter-lint
authority so CI cannot be the first place a bad head is judged.

Custody: no tokens here. Push authentication is the dispatcher clone's
ambient deploy key (core.sshCommand, B4.3 install). Model credentials,
gateway tokens, and the bot PAT never enter this module.
"""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dispatcher as _dp  # noqa: E402  (DEFAULT_LANES_ROOT; no cycle: dispatcher imports nothing local)
import frontmatter_lint  # noqa: E402
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
    """Collect exactly the declared outputs. Missing/oversized/escaping/
    unreadable entries refuse the WHOLE harvest — a partial delivery is a
    defect, not a delivery (required_outputs is the complete manifest)."""
    if not required_outputs:
        raise HarvestRefused(
            "envelope declares no required_outputs — nothing can ship; fix "
            "the envelope (ADR-B006: the field is the delivery manifest)"
        )
    workspace = Path(workspace)
    try:
        ws_ok = workspace.is_dir()
    except OSError as exc:  # unreadable parent — refusal, not a crash
        raise HarvestRefused(
            f"workspace {workspace} unreadable "
            f"({exc.__class__.__name__}: {exc})"
        )
    if not ws_ok:
        raise HarvestRefused(f"workspace {workspace} does not exist/not a dir")
    out: list[Collected] = []
    problems: list[str] = []
    for rel in required_outputs:
        try:
            src = _resolve_inside(workspace, rel)
            if not src.is_file():
                problems.append(
                    f"required output {rel!r}: missing from workspace")
                continue
            data = src.read_bytes()
        except HarvestRefused as exc:
            problems.append(str(exc))
            continue
        except OSError as exc:
            # Owner finding 3 (2026-07-23, req-1 gap): sandbox turns leave
            # files mode 600 the dispatcher group cannot read; that crashed
            # the live harvest with a raw traceback and NO episodic event.
            # Unreadable input is a REFUSAL — loud and episodic by contract.
            problems.append(
                f"required output {rel!r}: unreadable "
                f"({exc.__class__.__name__}: {exc}) — see SOP "
                "'workspace permissions durability'"
            )
            continue
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


# --------------------------------------------------- front matter (finding 6)

_FM_FENCE_RE = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*(?:\n|\Z)", re.DOTALL)


def strip_leading_front_matter(text: str) -> str:
    """Remove a leading front-matter fence (the agent's, if any) so the
    canonical stamp can never be preceded or duplicated."""
    return _FM_FENCE_RE.sub("", text, count=1)


def stamp_front_matter(body: str, *, project_id: str, task_id: str, role: str,
                       handoff_rel: str, sensitivity: str,
                       slug: str | None = None) -> str:
    """Canonical §14 front matter for the delivered handoff, stamped
    mechanically (owner finding 6, 2026-07-23): every field derives from the
    envelope + clock, so drift between an agent-authored head and
    frontmatter-lint is impossible by construction — the live TASK-003 cycle
    burned an iteration teaching the schema inside acceptance_criteria.
    The agent's ten-section BODY and its gate-claim line stay untouched
    (content authorship remains with the role agent); the head is filing
    metadata, the same category as the commit trailers the harvest already
    writes. The stamp is schema-validated HERE so that if the artifact
    schema ever moves, the failure is an episodic dispatcher-side refusal,
    not a red CI run after the push."""
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    fm = {
        "artifact_id": handoff_rel,
        "title": (f"{task_id} {slug} delivery handoff" if slug
                  else f"{task_id} delivery handoff"),
        "type": "note",
        "project": project_id,
        "owner": f"{role} (agent session, §86-C6 attribution)",
        "version": "1.0",
        "status": "READY_FOR_REVIEW",
        "sensitivity": sensitivity,
        "created": today,
        "updated": today,
    }
    problems = frontmatter_lint.schema_problems(dict(fm))
    if problems:
        raise HarvestRefused(
            "canonical front-matter stamp fails the artifact schema — the "
            "stamp and control/schemas/frontmatter.json have drifted; "
            "refusing dispatcher-side rather than shipping a red PR: "
            + "; ".join(problems)
        )
    head = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    stripped = strip_leading_front_matter(body).lstrip("\n")
    return f"---\n{head}---\n\n{stripped}"


def frontmatter_problems(items: list[Collected]) -> list[str]:
    """Pre-validate delivered Markdown against the SAME authority CI's
    frontmatter-lint applies at merge (owner finding 6): a bad head on any
    delivered .md red-flags the PR only AFTER the push — too late for the
    episodic-refusal contract. Mirrors the lint's rules: a leading fence
    must parse and validate; files under the required-front-matter dirs
    (except README.md) must carry one; excluded trees are skipped."""
    problems: list[str] = []
    for item in items:
        rel = item.rel_path
        if not rel.endswith(".md"):
            continue
        if rel.split("/", 1)[0] in frontmatter_lint.EXCLUDED_TOP_LEVEL:
            continue
        text = item.data.decode("utf-8", errors="replace")
        try:
            fm_text = frontmatter_lint.extract_front_matter(text)
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        required = rel.startswith(
            tuple(d + "/" for d in frontmatter_lint.REQUIRED_FM_DIRS)
        ) and not rel.endswith("/README.md")
        if fm_text is None:
            if required:
                problems.append(
                    f"{rel}: front matter required in this directory")
            continue
        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: front matter is not valid YAML ({exc})")
            continue
        if not isinstance(data, dict):
            problems.append(f"{rel}: front matter must be a YAML mapping")
            continue
        problems.extend(
            f"{rel}: {p}" for p in frontmatter_lint.schema_problems(data))
    return problems


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
    lanes_root: Path = None

    def __post_init__(self):
        self.repo_root = Path(self.repo_root)
        # ADR-B007: delivery worktrees relocate OUT of the clone to the
        # shared lanes root (/srv/company/lanes/.delivery/) — same
        # nested-tree-contamination rationale as the state lanes.
        self.lanes_root = Path(self.lanes_root or _dp.DEFAULT_LANES_ROOT)
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
        wt = self.lanes_root / ".delivery" / branch.replace("/", "-")
        wt.parent.mkdir(parents=True, exist_ok=True)
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
    data_classification: str | None = None,
    harvester: GitHarvester | None = None,
) -> dict:
    """Full harvest pipeline: collect -> secret-scan -> front-matter
    pre-check -> handoff stamp+pre-check -> branch/commit/push. Raises
    HarvestRefused (episodic, binding req 1) on any content defect;
    HarvestError on infrastructure failure. Returns {branch, sha, files}
    on success."""
    role_lc = role.lower()
    branch = f"{role_lc}/{task_id}" + (f"-{slug}" if slug else "")

    items = collect(workspace, required_outputs)

    findings = secret_scan(items)
    if findings:
        raise HarvestRefused(
            "secret scan hit — delivery refused BEFORE any commit/push "
            "(ADR-B006 binding requirement 2): " + "; ".join(findings)
        )

    fm_problems = frontmatter_problems(items)
    if fm_problems:
        raise HarvestRefused(
            "delivered front matter fails the artifact schema "
            "(dispatcher-side pre-validation, same authority as CI "
            "frontmatter-lint): " + "; ".join(fm_problems)
        )

    handoff_src = Path(workspace) / "handoff.md"
    try:
        if not handoff_src.is_file():
            raise HarvestRefused(
                "workspace has no handoff.md — the agent-authored §15 "
                "ten-section handoff is a standing required output "
                "(ADR-B006 item 4)"
            )
        raw_handoff = handoff_src.read_text(encoding="utf-8")
    except OSError as exc:
        # Owner finding 3 (2026-07-23): THIS read crashed the live harvest
        # with a raw traceback and no episodic event when a sandbox turn
        # left handoff.md mode 600. Refusal machinery, not a crash.
        raise HarvestRefused(
            f"workspace handoff.md unreadable "
            f"({exc.__class__.__name__}: {exc}) — see SOP 'workspace "
            "permissions durability' (ADR-B006 req 1: loud, episodic, "
            "never a traceback)"
        )
    except UnicodeDecodeError as exc:
        raise HarvestRefused(f"workspace handoff.md is not valid UTF-8 ({exc})")

    handoff_rel = f"projects/{project_id}/episodes/{task_id}/handoff.md"
    handoff_body = stamp_front_matter(
        raw_handoff, project_id=project_id, task_id=task_id, role=role,
        handoff_rel=handoff_rel,
        sensitivity=data_classification or "internal", slug=slug,
    )
    problems = validate_handoff(handoff_body, branch)
    if problems:
        raise HarvestRefused(
            "handoff.md fails handoff_check (dispatcher-side pre-validation; "
            "CI is the backstop, not the first gate): " + "; ".join(problems)
        )
    if secret_scan([Collected("handoff.md", handoff_src,
                              handoff_body.encode("utf-8"))]):
        raise HarvestRefused("secret scan hit in handoff.md — delivery refused")

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
