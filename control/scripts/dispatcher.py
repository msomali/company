#!/usr/bin/env python3
"""Dispatcher core (B4.2 part 1) — v2 §82 items 2, 3, 4, 6, 7.

Scope of this module (PR 1 of the owner-approved B4.2 split):
  * §82.2 dispatch: role → agent resolution (manifests, §48.3), separation of
    duties, prompt assembly (digest reference, envelope, artifact links),
    spawn via an injectable session backend, run-id recording.
  * §82.3 retry classes, tier caps, loop detection → BLOCKED + ESC record.
  * §82.4 state transitions: Appendix A machine; every transition updates
    state.yaml, appends history with evidence, and commits (injectable
    committer; only the dispatcher and CI write state.yaml).
  * §82.6 logs: every action appends to episodes/TASK-###/log.jsonl.
  * §82.7 onboarded-project rule: charter origin.type onboarded forces T3
    at the first DEPLOYMENT transition.

Deferred to part 2 (approvals + metering): §82.5 approvals capture, §82.8
token metering / cost ceilings / concurrency queue.

The dispatcher never runs inside an agent context (BA-1.4); during bootstrap
it is exercised only by tests with a fake backend. Real sessions_spawn wiring
is part of B4.3 installation, executed by the human.
"""
from __future__ import annotations

import datetime
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "control" / "manifests"
DIGEST_PATH = REPO_ROOT / "company" / "digest-v1.1.md"

# ADR-B007: the state lane is a persistent git worktree SIBLING to the clone,
# never nested inside it (nested trees contaminate scans — the PR #122
# gate-records gap). One root, shared with the delivery worktrees
# (harvest.py imports this). Production layout: clone at /srv/company/repo,
# lanes at /srv/company/lanes/TASK-### — same owner (dispatcher:dispatcher).
DEFAULT_LANES_ROOT = Path("/srv/company/lanes")
# State/episode commits are dispatcher-authored (§80.5 infrastructure lane).
DISPATCHER_NAME = "dispatcher"
DISPATCHER_EMAIL = "dispatcher@company.local"

# ---------------------------------------------------------------- state machine

# Appendix A reference workflow. Forward edges; review states loop through
# REMEDIATION; BLOCKED is reachable from every non-terminal state and resumes
# to the state recorded in history.
FORWARD = [
    "INTAKE",
    "DISCOVERY",
    "REQUIREMENTS",
    "DESIGN",
    "DELIVERY_PLAN",
    "IMPLEMENTATION",
    "QUALITY_REVIEW",
    "SECURITY_REVIEW",
    "PRIVACY_COMPLIANCE_REVIEW",
    "PRODUCTION_READINESS",
    "PRODUCT_ACCEPTANCE",
    "HUMAN_RELEASE_AUTHORIZATION",
    "DEPLOYMENT",
    "PRODUCTION_VERIFICATION",
    "OPERATIONS_AND_FEEDBACK",
    "CLOSED",
]
REVIEW_STATES = {"QUALITY_REVIEW", "SECURITY_REVIEW", "PRIVACY_COMPLIANCE_REVIEW"}
TERMINAL = {"CLOSED"}


def legal_transitions(state: str) -> set[str]:
    if state in TERMINAL:
        return set()
    out: set[str] = {"BLOCKED"}
    if state == "BLOCKED":
        # resume target is validated against history by transition()
        return (set(FORWARD) - {"INTAKE"}) | {"REMEDIATION"}
    if state == "REMEDIATION":
        return REVIEW_STATES | {"BLOCKED"}
    idx = FORWARD.index(state)
    out.add(FORWARD[idx + 1])
    if state in REVIEW_STATES:
        out.add("REMEDIATION")
    return out


# ------------------------------------------------------------------- utilities

def _now() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


class GitCommitter:
    """Commits state/log changes. Injectable so tests never touch real git."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def commit(self, paths: list[Path], message: str) -> None:
        rels = [str(p.relative_to(self.repo_root)) for p in paths]
        subprocess.run(["git", "-C", str(self.repo_root), "add", *rels], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo_root), "commit", "-m", message],
            check=True, capture_output=True,
        )


class LaneError(RuntimeError):
    """Task-lane worktree operation failed (git/infrastructure defect)."""


@dataclass
class TaskLane:
    """ADR-B007 persistent state-lane worktree for one task.

    ``dispatch/TASK-###`` materializes at ``<lanes_root>/TASK-###`` — a git
    worktree SIBLING to the clone, never inside it. Reads and writes both
    resolve here (PR 2 wires the reads); the clone's own checkout is NEVER
    switched — which retires the branch-vintage finding (owner finding 1,
    2026-07-23) at its root: no state operation can revert the clone's
    ``control/scripts`` to a branch's tooling because no state operation
    touches the clone's checkout. Brand-new lanes base on freshly fetched
    ``origin/main`` (the vintage property pinned by test_branch_vintage
    carries over); an existing local/remote branch is attached as-is.

    Provenance unchanged (§80.5): commits are dispatcher-authored, pushed via
    the clone's ambient deploy key (B4.3 install — no tokens here). Injectable
    runner keeps tests offline. Modeled on GitHarvester's proven delivery
    worktree (PR #103), made PERSISTENT for the episode's life (``remove()``
    prunes it in the close runbook, PR 2).
    """

    repo_root: Path
    branch: str
    lanes_root: Path = DEFAULT_LANES_ROOT
    push: bool = True
    runner: object = None

    def __post_init__(self):
        self.repo_root = Path(self.repo_root)
        self.lanes_root = Path(self.lanes_root)
        self.runner = self.runner or self._default_runner

    @staticmethod
    def _default_runner(argv: list[str], cwd: Path):
        proc = subprocess.run(argv, cwd=str(cwd), capture_output=True,
                              text=True, timeout=300)
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    @property
    def path(self) -> Path:
        """The lane worktree: <lanes_root>/<last branch segment>."""
        return self.lanes_root / self.branch.split("/")[-1]

    def _git(self, *args: str, cwd: Path | None = None, check: bool = True):
        rc, out, err = self.runner(["git", *args], cwd or self.repo_root)
        if check and rc != 0:
            raise LaneError(
                f"git {' '.join(args[:2])}… failed ({rc}) on task-lane "
                f"{self.branch!r}: {err.strip()[:300]}"
            )
        return rc, out, err

    def ensure(self) -> Path:
        """Materialize the lane worktree if absent (persistent: a present
        worktree is reused). Returns the worktree path."""
        if self.path.exists():
            return self.path
        self.lanes_root.mkdir(parents=True, exist_ok=True)
        rc, _, _ = self._git("rev-parse", "--verify", "--quiet",
                             f"refs/heads/{self.branch}", check=False)
        if rc == 0:
            self._git("worktree", "add", str(self.path), self.branch)
            return self.path
        rc, _, _ = self._git("rev-parse", "--verify", "--quiet",
                             f"refs/remotes/origin/{self.branch}", check=False)
        if rc == 0:
            self._git("worktree", "add", "-B", self.branch, str(self.path),
                      f"origin/{self.branch}")
            return self.path
        # Brand-new lane: base on freshly fetched origin/main; loudly fall
        # back to local main (the vintage-immunity property, test-pinned).
        rc, _, _ = self._git("fetch", "origin", "main", check=False)
        base = "origin/main"
        if rc != 0:
            print(f"WARN task-lane: fetch origin/main failed; basing "
                  f"{self.branch} on local 'main'")
            base = "main"
        self._git("worktree", "add", "-b", self.branch, str(self.path), base)
        return self.path

    def commit_blobs(self, sources: dict[str, bytes], message: str) -> str:
        """Write ``{repo_rel_path: bytes}`` into the lane worktree, commit
        (dispatcher-authored), push. Returns the commit sha. The bytes are
        the source of truth — the caller reads them from wherever the runtime
        currently writes state (the clone tree in PR 1; the lane worktree
        itself in PR 2, where this becomes a same-file no-op copy)."""
        if not sources:
            raise LaneError("commit_blobs: nothing to commit (empty sources)")
        wt = self.ensure()
        for rel, data in sources.items():
            dest = wt / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        self._git("add", "--", *sources.keys(), cwd=wt)
        self._git(
            "-c", f"user.name={DISPATCHER_NAME}",
            "-c", f"user.email={DISPATCHER_EMAIL}",
            "commit", "-m", message, cwd=wt,
        )
        sha = self._git("rev-parse", "HEAD", cwd=wt)[1].strip()
        if self.push:
            self._git("push", "-u", "origin", self.branch, cwd=wt)
        return sha

    def remove(self) -> None:
        """Prune the lane worktree (close runbook, PR 2). Idempotent."""
        if self.path.exists():
            self._git("worktree", "remove", "--force", str(self.path),
                      check=False)
        self._git("worktree", "prune", check=False)


class TaskBranchCommitter(GitCommitter):
    """Commits episode/state changes onto the task's ``dispatch/TASK-###``
    lane — the branch SWITCH retires (ADR-B007).

    Prior behavior (owner finding 2, 2026-07-22) switched the clone's own
    checkout to the lane branch to commit, which is the branch-vintage
    finding's root (owner finding 1, 2026-07-23): the clone's tooling
    reverted to whatever branch it sat on. Now commits land in the task's
    persistent lane WORKTREE (``TaskLane``) sibling to the clone; the clone's
    checkout is never disturbed.

    Runtime contract preserved: ``commit(paths, message)`` where ``paths``
    are repo_root-relative working-tree files. The committer ferries their
    CURRENT content into the lane worktree and commits there — a copy, so the
    clone's readable state is never removed (PR 1 keeps reads coherent while
    reads still come from the clone). In ADR-B007 PR 2, ``task_dir`` resolves
    into the lane worktree directly, the ferried paths already live there,
    and this copy collapses to a no-op.
    """

    def __init__(self, repo_root: Path, branch: str, push: bool = True,
                 runner=None, lanes_root: Path = DEFAULT_LANES_ROOT):
        super().__init__(repo_root)
        self.branch = branch
        self.push = push
        self.lane = TaskLane(repo_root=repo_root, branch=branch,
                             lanes_root=lanes_root, push=push, runner=runner)

    def commit(self, paths: list[Path], message: str) -> None:
        sources = {
            str(Path(p).relative_to(self.repo_root)): Path(p).read_bytes()
            for p in paths
        }
        self.lane.commit_blobs(sources, message)


@dataclass
class DispatchError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


# ----------------------------------------------------------------- retry model

# §82.3 — class → (max_retries, backoff_seconds sequence)
RETRY_POLICY = {
    "transient_infra": (2, (30, 120)),
    "rate_limit": (2, (60, 300)),
    "tool_timeout": (1, (30,)),
    "format_failure": (1, (0,)),        # one reformat attempt
    "invalid_input": (0, ()),           # return to owner
    "policy_denial": (0, ()),
    "verification_failure": (0, ()),
}

TIER_CAPS = {  # tier → (wall_clock_minutes, tool_call_limit); T3 explicit
    "T1": (30, 25),
    "T2": (120, 100),
}


def retry_decision(failure_class: str, attempt: int) -> tuple[bool, int]:
    """(should_retry, backoff_seconds) for a failure of `failure_class` on
    0-indexed `attempt`."""
    if failure_class not in RETRY_POLICY:
        raise DispatchError(f"unknown failure class: {failure_class}")
    max_retries, backoffs = RETRY_POLICY[failure_class]
    if attempt >= max_retries:
        return False, 0
    return True, backoffs[attempt]


def effective_caps(envelope: dict) -> tuple[int, int]:
    """Tier caps are ceilings; a TIGHTER envelope budget always wins
    (§88.12 fix 2026-07-18 — previously T1/T2 envelope budgets were
    ignored, so a 1-tool-call budget silently became the tier's 100)."""
    tier = envelope["tier"]
    budgets = envelope.get("budgets") or {}
    if tier in TIER_CAPS:
        wall_cap, tool_cap = TIER_CAPS[tier]
        wall = budgets.get("wall_clock_minutes")
        tools = budgets.get("tool_call_limit")
        return (
            min(wall_cap, wall) if isinstance(wall, int) else wall_cap,
            min(tool_cap, tools) if isinstance(tools, int) else tool_cap,
        )
    # T3: explicit in envelope (schema-mandatory)
    return budgets["wall_clock_minutes"], budgets["tool_call_limit"]


# ------------------------------------------------------------------ dispatcher

@dataclass
class Dispatcher:
    repo_root: Path = REPO_ROOT
    backend: object = None            # must provide spawn(agent_id, prompt) -> run_id
    committer: object = None          # must provide commit(paths, message)
    manifest_dir: Path | None = None
    digest_path: Path | None = None
    _manifests: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.manifest_dir = self.manifest_dir or self.repo_root / "control/manifests"
        self.digest_path = self.digest_path or self.repo_root / "company/digest-v1.1.md"
        self.committer = self.committer or GitCommitter(self.repo_root)

    # -- episode helpers -------------------------------------------------

    def task_dir(self, project_id: str, task_id: str) -> Path:
        return self.repo_root / "projects" / project_id / "episodes" / task_id

    def _read(self, task_dir: Path, name: str) -> dict:
        return yaml.safe_load((task_dir / name).read_text(encoding="utf-8"))

    def log(self, task_dir: Path, event: str, **fields) -> Path:
        """§82.6 — every action appends to the episode package."""
        path = task_dir / "log.jsonl"
        record = {"at": _now(), "event": event, **fields}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        return path

    # -- state transitions (§82.4) ----------------------------------------

    def transition(self, task_dir: Path, to: str, evidence: str) -> dict:
        """Validate legality, rewrite state.yaml, append history, log, commit."""
        state = self._read(task_dir, "state.yaml")
        frm = state["state"]
        allowed = legal_transitions(frm)
        if to not in allowed:
            raise DispatchError(
                f"illegal transition {frm} → {to} (allowed: {sorted(allowed)})"
            )
        if frm == "BLOCKED":
            resumable = {h["from"] for h in state["history"] if h["to"] == "BLOCKED"}
            if to not in resumable:
                raise DispatchError(
                    f"BLOCKED resume must return to the pre-block state "
                    f"{sorted(resumable)}, not {to}"
                )
        if not evidence.strip():
            raise DispatchError("transition evidence must be non-empty (§82.4)")

        # §82.7 — onboarded projects force T3 at first DEPLOYMENT.
        if to == "DEPLOYMENT":
            self._enforce_onboarded_rule(task_dir)

        state["state"] = to
        state["history"].append(
            {"at": _now(), "from": frm, "to": to, "evidence": evidence}
        )
        if to == "BLOCKED":
            state["rejection_cycles"] = state.get("rejection_cycles", 0)
        path = task_dir / "state.yaml"
        path.write_text(
            yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        log_path = self.log(task_dir, "transition", frm=frm, to=to, evidence=evidence)
        self.committer.commit(
            [path, log_path],
            f"{state['task_id']}: {frm} → {to} [{evidence}]",
        )
        return state

    def _enforce_onboarded_rule(self, task_dir: Path) -> None:
        task = self._read(task_dir, "task.yaml")
        charter = task_dir.parents[1] / "charter.md"
        if not charter.exists():
            return
        text = charter.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            fm = yaml.safe_load(text[3:end]) or {}
            origin = fm.get("origin") or {}
            if isinstance(origin, dict) and origin.get("type") == "onboarded":
                if task.get("tier") != "T3":
                    task["tier"] = "T3"
                    (task_dir / "task.yaml").write_text(
                        yaml.safe_dump(task, sort_keys=False, allow_unicode=True),
                        encoding="utf-8",
                    )
                    self.log(
                        task_dir, "tier_forced",
                        reason="v1 §57.6 onboarded project reaching DEPLOYMENT",
                        tier="T3",
                    )

    # -- dispatch (§82.2) --------------------------------------------------

    def resolve_agent(self, role: str) -> dict:
        path = self.manifest_dir / f"{role.lower()}.yaml"
        if not path.exists():
            raise DispatchError(f"no manifest for role {role}")
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        return manifest

    def build_prompt(self, envelope: dict) -> str:
        """v1 §48.2: envelope + digest (inline for T2/T3, reference for T1) +
        artifact links. Sub-agents get no ambient context."""
        parts = []
        if envelope["tier"] in ("T2", "T3"):
            parts.append(self.digest_path.read_text(encoding="utf-8"))
        else:
            parts.append(
                "Constitution digest: company/digest-v1.1.md (v1.1, binding)."
            )
        parts.append("## Task envelope\n\n```yaml\n"
                     + yaml.safe_dump(envelope, sort_keys=False) + "```")
        inputs = envelope.get("inputs") or []
        if inputs:
            links = "\n".join(f"- {i['artifact_id']}" for i in inputs)
            parts.append(f"## Input artifacts\n\n{links}")
        return "\n\n".join(parts)

    def dispatch(self, project_id: str, task_id: str) -> str:
        if self.backend is None:
            raise DispatchError(
                "no session backend configured — during bootstrap the "
                "dispatcher is test-only (BA-2.4: no agent activation)"
            )
        task_dir = self.task_dir(project_id, task_id)
        envelope = self._read(task_dir, "task.yaml")
        state = self._read(task_dir, "state.yaml")
        if state["state"] == "BLOCKED":
            raise DispatchError("task is BLOCKED; resolve the escalation first")

        role = envelope["assigned_role"]
        if envelope["requested_by"] == role:
            raise DispatchError(
                "separation of duties: requester and assignee identical (v1 §8)"
            )
        manifest = self.resolve_agent(role)
        if manifest.get("status") != "active":
            raise DispatchError(
                f"agent {role} is {manifest.get('status')!r}, not 'active' — "
                "activation is a human act (BA-2.4); dispatch refused"
            )

        prompt = self.build_prompt(envelope)
        run_id = self.backend.spawn(agent_id=role.lower(), prompt=prompt)

        state["run_id"] = run_id
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        path = task_dir / "state.yaml"
        path.write_text(
            yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        log_path = self.log(task_dir, "dispatch", role=role, run_id=run_id)
        self.committer.commit(
            [path, log_path], f"{task_id}: dispatched to {role} [{run_id}]"
        )
        return run_id

    # -- breaker (§82.3 / §88.12) -------------------------------------------

    def record_action(self, task_dir: Path, fingerprint: str, **fields) -> int:
        """Record one tool action against the effective tool-call cap.

        §88.12 breaker (added 2026-07-18 — no counting enforcement existed
        before this): BLOCKED tasks refuse further actions; the action that
        exceeds the cap is logged as evidence, then the task is BLOCKED
        with an ESC record and the caller gets a typed error — no retry
        loop is possible because both this method and dispatch() refuse
        BLOCKED tasks. Returns the running action count.
        """
        state = self._read(task_dir, "state.yaml")
        if state["state"] == "BLOCKED":
            raise DispatchError(
                "task is BLOCKED; no further actions (§82.3 — resolve the "
                "escalation first)"
            )
        envelope = self._read(task_dir, "task.yaml")
        wall_cap, tool_cap = effective_caps(envelope)

        # §15/§82.3 wall-clock breaker (owner ruling 2026-07-18: core safety,
        # not deferrable — an agent that cannot be time-bounded is as
        # dangerous as one that cannot be call-bounded). Task start = first
        # history timestamp; the over-deadline action is logged as evidence,
        # then the task is BLOCKED with an ESC record — same no-retry
        # semantics as the tool-cap path.
        started_raw = str((state.get("history") or [{}])[0].get("at", ""))
        if started_raw:
            started = datetime.datetime.fromisoformat(
                started_raw.replace("Z", "+00:00")
            )
            elapsed_min = (
                datetime.datetime.now(datetime.timezone.utc) - started
            ).total_seconds() / 60
            if elapsed_min > wall_cap:
                self.log(task_dir, "action", fingerprint=fingerprint, **fields)
                esc = self.block_with_escalation(
                    task_dir,
                    f"wall_clock_minutes {wall_cap} exceeded "
                    f"(elapsed {elapsed_min:.1f} min since {started_raw})",
                )
                raise DispatchError(
                    f"breaker: wall_clock_minutes {wall_cap} exceeded "
                    f"({elapsed_min:.1f} min elapsed) — task BLOCKED "
                    f"({esc.name})"
                )
        log_path = task_dir / "log.jsonl"
        prior = 0
        if log_path.exists():
            prior = sum(
                1 for line in log_path.read_text(encoding="utf-8").splitlines()
                if json.loads(line).get("event") == "action"
            )
        self.log(task_dir, "action", fingerprint=fingerprint, **fields)
        count = prior + 1
        if count > tool_cap:
            esc = self.block_with_escalation(
                task_dir,
                f"tool_call_limit {tool_cap} exceeded (action #{count})",
            )
            raise DispatchError(
                f"breaker: tool_call_limit {tool_cap} exceeded at action "
                f"#{count} — task BLOCKED ({esc.name})"
            )
        loop = self.check_loops(task_dir)
        if loop:
            self.block_with_escalation(task_dir, loop)
            raise DispatchError(f"loop cap: {loop} — task BLOCKED")
        return count

    # -- loop detection (§82.3) ---------------------------------------------

    def check_loops(self, task_dir: Path) -> str | None:
        """Return an ESC reason if a loop cap is hit, else None.
        Detects: identical action ×3 (consecutive identical action
        fingerprints in the log) and rejection_cycles ≥ 2."""
        state = self._read(task_dir, "state.yaml")
        if state.get("rejection_cycles", 0) >= 2:
            return "rejection cycles ≥ 2"
        log_path = task_dir / "log.jsonl"
        if log_path.exists():
            fingerprints = []
            for line in log_path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec.get("event") == "action":
                    fingerprints.append(rec.get("fingerprint"))
            for i in range(len(fingerprints) - 2):
                if (fingerprints[i] == fingerprints[i + 1] == fingerprints[i + 2]
                        and fingerprints[i] is not None):
                    return "identical action ×3"
        return None

    def block_with_escalation(self, task_dir: Path, reason: str) -> Path:
        """Loop/dead-letter path: BLOCKED + ESC record (v2 §78 row 7)."""
        state = self._read(task_dir, "state.yaml")
        task_id = state["task_id"]
        esc_path = task_dir / f"ESC-{task_id}.md"
        today = _now()[:10]
        esc_path.write_text(
            "---\n"
            f"artifact_id: {esc_path.relative_to(self.repo_root)}\n"
            f"title: ESC — {task_id} blocked ({reason})\n"
            "type: escalation\n"
            f"project: {task_dir.parents[1].name}\n"
            "owner: dispatcher\n"
            'version: "1.0"\n'
            "status: BLOCKED\n"
            "sensitivity: internal\n"
            f"created: {today}\n"
            f"updated: {today}\n"
            "---\n\n"
            f"# {task_id} blocked by dispatcher\n\n"
            f"Reason: {reason} (v2 §82.3 loop caps).\n\n"
            "Owner decision required; task will not be re-dispatched until this\n"
            "record is resolved and the state is transitioned out of BLOCKED.\n",
            encoding="utf-8",
        )
        self.transition(task_dir, "BLOCKED", evidence=str(esc_path.name))
        return esc_path
