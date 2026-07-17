#!/usr/bin/env python3
"""Approvals capture (B4.2 part 2) — v2 §82.5 under the §51 interim channel.

Owner design constraints (2026-07-17, recorded verbatim in the B4.2/2 PR):
  * Gate approvals of record bind to the HUMAN OWNER's GitHub identity per the
    §51 record. A bot review NEVER satisfies a gate approval — this is
    distinct from ADR-B005's code-owner workaround, which applies only to
    owner-authored PRs and merge mechanics, never to gate decisions.
  * No approval inference: absence of a decision is not a decision; malformed
    decisions are not decisions.
  * No timeout-proceeds: an overdue approval leaves the task BLOCKED/waiting;
    the dispatcher never advances state on elapsed time.

Interim channel (§51 register): the approval of record is a PR review by the
owner. The textual `APPROVE/REJECT <task-id> <gate>` format is parsed from
the review/message body when the dispatcher runtime is wired (B4.3);
this module implements parsing, authorization, gate-record emission
(control/schemas/gate.json), and the state transition per gate.
"""
from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCHEMA = REPO_ROOT / "control" / "schemas" / "gate.json"
REGISTER_GLOB = "control/registers/*.md"

GATES = ("SAT", "SSE", "DPC", "DCE", "PJM", "HUMAN")

# Gate → (state the task must be in, state an APPROVE advances it to)
GATE_TRANSITIONS = {
    "SAT": ("QUALITY_REVIEW", "SECURITY_REVIEW"),
    "SSE": ("SECURITY_REVIEW", "PRIVACY_COMPLIANCE_REVIEW"),
    "DPC": ("PRIVACY_COMPLIANCE_REVIEW", "PRODUCTION_READINESS"),
    "DCE": ("PRODUCTION_READINESS", "PRODUCT_ACCEPTANCE"),
    "PJM": ("PRODUCT_ACCEPTANCE", "HUMAN_RELEASE_AUTHORIZATION"),
    "HUMAN": ("HUMAN_RELEASE_AUTHORIZATION", "DEPLOYMENT"),
}

# Gate rejection returns the task to REMEDIATION (review gates) or blocks
# forward motion where REMEDIATION is not an Appendix A edge.
REJECT_TARGET = {
    "SAT": "REMEDIATION",
    "SSE": "REMEDIATION",
    "DPC": "REMEDIATION",
    "DCE": "BLOCKED",
    "PJM": "BLOCKED",
    "HUMAN": "BLOCKED",
}

DECISION_RE = re.compile(
    r"^\s*(APPROVE|REJECT)\s+(TASK-[0-9]{3,})\s+(\w+)\s*(?:[:—-]\s*(.*))?$",
    re.MULTILINE,
)


class ApprovalError(Exception):
    pass


@dataclass(frozen=True)
class Decision:
    verb: str          # APPROVE | REJECT
    task_id: str
    gate: str
    approver: str      # GitHub login of the reviewer
    reference: str     # PR review URL / message ref — evidence of record
    note: str = ""


def owner_identity(repo_root: Path = REPO_ROOT) -> str:
    """The §51 named owner's GitHub login, parsed from the owner-signed
    register record. Refuses to guess: no register → no approvals."""
    for path in sorted(repo_root.glob(REGISTER_GLOB)):
        text = path.read_text(encoding="utf-8")
        m = re.search(r"Named owner\s*\|[^|]*GitHub:\s*@([A-Za-z0-9-]+)", text)
        if m:
            return m.group(1)
    raise ApprovalError(
        "no §51 owner register found under control/registers/ — approvals "
        "capture cannot operate without a signed owner record (B0.4)"
    )


def parse_decisions(body: str, approver: str, reference: str) -> list[Decision]:
    """Extract well-formed decision lines. Malformed lines are IGNORED, never
    inferred (owner constraint: no approval inference)."""
    out = []
    for verb, task_id, gate, note in DECISION_RE.findall(body or ""):
        if gate in GATES:
            out.append(Decision(verb, task_id, gate, approver, reference,
                                (note or "").strip()))
    return out


class ApprovalsCapture:
    """Applies owner decisions to task episodes via the dispatcher."""

    def __init__(self, dispatcher, repo_root: Path = REPO_ROOT,
                 owner: str | None = None):
        self.dispatcher = dispatcher
        self.repo_root = repo_root
        self.owner = owner or owner_identity(repo_root)
        self._validator = Draft7Validator(
            json.loads((repo_root / "control/schemas/gate.json").read_text())
        )

    # -- authorization ----------------------------------------------------

    def authorize(self, decision: Decision) -> None:
        """Gate approvals bind to the §51 owner identity. Everything else —
        bot reviews included — is refused loudly."""
        if decision.approver != self.owner:
            raise ApprovalError(
                f"approval of record requires the §51 owner (@{self.owner}); "
                f"got @{decision.approver} — a bot or third-party review never "
                "satisfies a gate approval"
            )

    # -- application -------------------------------------------------------

    def apply(self, project_id: str, decision: Decision) -> Path:
        self.authorize(decision)
        task_dir = self.dispatcher.task_dir(project_id, decision.task_id)
        if not task_dir.exists():
            raise ApprovalError(f"unknown task {decision.task_id}")
        state = yaml.safe_load((task_dir / "state.yaml").read_text())
        expected, advance_to = GATE_TRANSITIONS[decision.gate]
        if state["state"] != expected:
            raise ApprovalError(
                f"{decision.gate} gate decision requires state {expected}; "
                f"task is in {state['state']} — no inference, no reordering"
            )

        record = self._gate_record(task_dir, decision)
        record_path = self._write_record(task_dir, decision, record)

        if decision.verb == "APPROVE":
            self.dispatcher.transition(
                task_dir, advance_to,
                evidence=f"{decision.gate} gate APPROVED by @{decision.approver}: "
                         f"{decision.reference}",
            )
        else:
            self._bump_rejection_cycles(task_dir)
            target = REJECT_TARGET[decision.gate]
            self.dispatcher.transition(
                task_dir, target,
                evidence=f"{decision.gate} gate REJECTED by @{decision.approver}: "
                         f"{decision.reference}",
            )
            loop = self.dispatcher.check_loops(task_dir)
            if loop and yaml.safe_load(
                (task_dir / "state.yaml").read_text()
            )["state"] != "BLOCKED":
                self.dispatcher.block_with_escalation(task_dir, loop)
        return record_path

    # -- internals ----------------------------------------------------------

    def _gate_record(self, task_dir: Path, decision: Decision) -> dict:
        now = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z")
        )
        task = yaml.safe_load((task_dir / "task.yaml").read_text())
        # A gate may be decided again after remediation; each decision is its
        # own immutable record, sequence-numbered within the task.
        gates_dir = task_dir.parents[1] / "gates"
        seq = 1 + sum(
            1 for p in gates_dir.glob(f"GATE-{decision.task_id}-{decision.gate}-*.yaml")
        ) if gates_dir.exists() else 1
        record = {
            "gate_id": f"GATE-{decision.task_id}-{decision.gate}-{seq}",
            "artifact_or_release": ", ".join(task["required_outputs"]),
            "gate_owner": decision.gate,
            "decision": "APPROVED" if decision.verb == "APPROVE" else "REJECTED",
            "criteria_version": "policy-set-v0",
            "evidence": [decision.reference],
            "findings": [decision.note] if decision.note else [],
            "next_owner": (
                GATE_TRANSITIONS[decision.gate][1]
                if decision.verb == "APPROVE"
                else REJECT_TARGET[decision.gate]
            ),
            "decided_at": now,
            "approval_message_ref": decision.reference,
        }
        errors = [e.message for e in self._validator.iter_errors(record)]
        if errors:
            raise ApprovalError(f"generated gate record invalid: {errors}")
        return record

    def _write_record(self, task_dir: Path, decision: Decision,
                      record: dict) -> Path:
        gates_dir = task_dir.parents[1] / "gates"
        gates_dir.mkdir(exist_ok=True)
        path = gates_dir / f"{record['gate_id']}.yaml"
        if path.exists():
            raise ApprovalError(
                f"gate record {path.name} already exists — decisions are "
                "immutable; supersession requires a new task cycle"
            )
        path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        self.dispatcher.log(
            task_dir, "gate_decision",
            gate=decision.gate, decision=record["decision"],
            approver=decision.approver, record=str(path.name),
        )
        return path

    def _bump_rejection_cycles(self, task_dir: Path) -> None:
        state_path = task_dir / "state.yaml"
        state = yaml.safe_load(state_path.read_text())
        state["rejection_cycles"] = state.get("rejection_cycles", 0) + 1
        state_path.write_text(
            yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
