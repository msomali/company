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
    tier = envelope["tier"]
    if tier in TIER_CAPS:
        return TIER_CAPS[tier]
    budgets = envelope["budgets"]  # T3: explicit in envelope (schema-mandatory)
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
