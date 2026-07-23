#!/usr/bin/env python3
"""OpenClaw session backend — activation item 1 (real session-spawn wiring).

The recorded/fake backend stays the unit-test fixture; this module is the
production ``backend`` object for ``Dispatcher.dispatch()`` (interface:
``spawn(agent_id, prompt) -> run_id``, dispatcher.py §82.2).

Mechanism (owner-approved proposal, 2026-07-21):

* One spawn = one agent turn via the ``openclaw agent`` CLI against the
  loopback gateway (docs cli/agent — "run one agent turn from scripts").
  The CLI is the maintained reference client (device handshake, pairing,
  protocol negotiation); no raw-WS reimplementation, no new Python deps.
* ``run_id`` = the session key this backend mints:
  ``agent:<agent_id>:<task-###>-<utcstamp>-<nonce>``. Durable and
  addressable later (sessions tooling / transcripts). The task fragment is
  parsed from the envelope block of the prompt when present. A fresh session
  per dispatch is deliberate: retries are clean-room (v1 §48.2 — sub-agents
  get no ambient context).
* Model policy: NO ``--model`` is passed. Per-role primary/fallback lives in
  the gateway's ``agents.list`` (generated from policies.yaml by
  agents_config_gen.py), so OpenClaw's documented failover applies: auth
  rotation inside the provider, then turn-local model fallback down the
  configured chain (docs concepts/model-failover). MODEL-001/002 hold by
  construction of policies.yaml.
* Agent-id resolution is SEAT-side, not gateway-side: the CLI validates
  ``--agent`` against the invoking user's config before connecting
  (agent-via-gateway.ts; first-live-spawn failure 2026-07-21). The
  dispatcher seat therefore carries ``OPENCLAW_CONFIG_PATH=
  /etc/company/openclaw-dispatcher.json`` — the same generated artifact,
  installed verbatim — in dispatcher.env. This backend passes the env
  through untouched; the SOP seat-check verifies resolution pre-live.
* Custody: model credentials never leave the gateway user (Mode S,
  ADR-B003). This process carries only ``OPENCLAW_GATEWAY_TOKEN``
  (+ optional ``OPENCLAW_GATEWAY_URL``), provided by
  /etc/company/dispatcher.env (systemd EnvironmentFile) or a sourced env for
  interactive one-shots. Values are never logged; error excerpts are
  scrubbed before they reach exceptions or logs.
* Concurrency: in-process ``metering.SessionPool``
  (mode_s.concurrency_cap). TODO (deferred 2026-07-21, owner answer 3;
  backlog entry beside declaration item 8): file-locked cross-process slot
  registry for the multi-agent era — activation day is one-shot-only,
  single operator, so a cross-process cap structurally cannot be exceeded.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from metering import SessionPool

DEFAULT_GATEWAY_URL = "ws://127.0.0.1:18789"
TOKEN_VAR = "OPENCLAW_GATEWAY_TOKEN"
URL_VAR = "OPENCLAW_GATEWAY_URL"
TASK_RE = re.compile(r"^\s*task_id:\s*['\"]?(TASK-\d+)", re.MULTILINE)


class SpawnError(RuntimeError):
    """Spawn attempted and failed (CLI error, timeout, bad response)."""


def extract_turn_meta(response: dict | None) -> dict:
    """Turn metadata from ``openclaw agent --json`` output.

    Two shapes exist (owner finding 3, 2026-07-22 — the first live turn
    reported durationMs=None because only one was read): the gateway path
    wraps the run result — ``{status, runId, result: {payloads, meta}}``
    (agent-via-gateway.ts) — while the embedded fallback emits
    ``{payloads, meta}`` at top level. ``durationMs`` lives in ``meta`` on
    either shape.
    """
    if not isinstance(response, dict):
        return {}
    meta = response.get("meta")
    if not isinstance(meta, dict):
        result = response.get("result")
        meta = result.get("meta") if isinstance(result, dict) else None
    return meta if isinstance(meta, dict) else {}


class SpawnRefused(SpawnError):
    """Refused before any gateway contact (pre-flight): unknown agent,
    missing token, concurrency cap. Nothing was spawned."""


def default_runner(argv: list[str], env: dict, timeout_s: float):
    """Run the CLI; returns (returncode, stdout, stderr). Raises SpawnRefused
    when the binary is absent (install pre-flight not done) and SpawnError on
    a hard wall-clock overrun (grace past the CLI's own --timeout)."""
    try:
        proc = subprocess.run(
            argv, env=env, capture_output=True, text=True, timeout=timeout_s
        )
    except FileNotFoundError as exc:
        raise SpawnRefused(
            f"openclaw CLI not found ({argv[0]!r}) — system-wide install is an "
            "activation pre-flight PREREQUISITE (control/sops/"
            "dispatcher-install.md addendum)"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SpawnError(
            f"openclaw agent exceeded the hard wall clock ({timeout_s:.0f}s "
            "incl. grace) — turn state unknown; check the session transcript "
            "before any retry (docs cli/agent: transport loss is ambiguous)"
        ) from exc
    return proc.returncode, proc.stdout or "", proc.stderr or ""


@dataclass
class OpenClawSessionBackend:
    """Spawns one real agent turn per dispatch via the loopback gateway.

    ``timeout_seconds`` is the per-turn deadline passed to the CLI as
    ``--timeout``; the runtime one-shot sets it from the task's effective
    wall-clock cap (§82.3). Live-observation item (owner requirement B,
    2026-07-21): whether that deadline is total or per-attempt across
    OpenClaw's up-to-10× overload retries is observed on the first live
    one-shot, not assumed.
    """

    policies_path: Path
    gateway_url: str = DEFAULT_GATEWAY_URL
    timeout_seconds: int = 3600
    openclaw_bin: str = "openclaw"
    runner: object = None          # (argv, env, timeout_s) -> (rc, out, err)
    env: dict | None = None        # default: os.environ at spawn time
    pool: SessionPool | None = None

    def __post_init__(self):
        self.runner = self.runner or default_runner
        self.policies_path = Path(self.policies_path)
        self.pool = self.pool or SessionPool(self.policies_path)
        policies = yaml.safe_load(
            self.policies_path.read_text(encoding="utf-8")
        ) or {}
        self.known_agents = {c.lower() for c in (policies.get("agents") or {})}
        self.last_response: dict | None = None

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _scrub(text: str, token: str) -> str:
        """Never let the gateway token reach an exception message or log."""
        return text.replace(token, "***") if token else text

    @staticmethod
    def _mint_run_id(agent_id: str, prompt: str) -> str:
        m = TASK_RE.search(prompt)
        frag = m.group(1).lower() if m else "adhoc"
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%dt%H%M%Sz"
        )
        return f"agent:{agent_id}:{frag}-{stamp}-{uuid.uuid4().hex[:6]}"

    # -- interface (dispatcher.py §82.2) -----------------------------------

    def spawn(self, agent_id: str, prompt: str) -> str:
        if agent_id not in self.known_agents:
            raise SpawnRefused(
                f"unknown agent id {agent_id!r} — not an agents key in "
                f"{self.policies_path} (drift between manifests and model "
                "policies; refusing rather than spawning into a nonexistent "
                "gateway agent)"
            )
        env = dict(self.env if self.env is not None else os.environ)
        token = (env.get(TOKEN_VAR) or "").strip()
        if not token:
            raise SpawnRefused(
                f"{TOKEN_VAR} missing/empty in the environment — provision it "
                "via /etc/company/dispatcher.env (SECRETS-MANIFEST; names "
                "only in the repo). Nothing spawned."
            )
        env.setdefault(URL_VAR, self.gateway_url)

        run_id = self._mint_run_id(agent_id, prompt)
        if not self.pool.request(run_id):
            # A refused one-shot must leave NO residue: request() queued the
            # run_id FIFO, and a later release() would grant that phantom a
            # slot nobody ever releases. Queueing is daemon-era semantics.
            if run_id in self.pool.queue:
                self.pool.queue.remove(run_id)
            raise SpawnRefused(
                f"concurrency cap {self.pool.cap} reached "
                "(mode_s.concurrency_cap) — one-shot refuses rather than "
                "queues. Cross-process slot registry deferred 2026-07-21 "
                "(declaration backlog, beside item 8)."
            )
        msg_path: str | None = None
        try:
            fd, msg_path = tempfile.mkstemp(prefix="dispatch-", suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:  # mkstemp = 0600
                fh.write(prompt)
            argv = [
                self.openclaw_bin, "agent",
                "--agent", agent_id,
                "--session-key", run_id,
                "--message-file", msg_path,
                "--json",
                "--timeout", str(int(self.timeout_seconds)),
            ]
            rc, out, err = self.runner(argv, env, self.timeout_seconds + 120)
            if rc != 0:
                raise SpawnError(
                    f"openclaw agent exited {rc} for {run_id}: "
                    f"{self._scrub((err or out).strip(), token)[:500]}"
                )
            try:
                response = json.loads(out)
            except json.JSONDecodeError as exc:
                raise SpawnError(
                    f"unparseable --json output for {run_id}: "
                    f"{self._scrub(out.strip(), token)[:200]}"
                ) from exc
            status = str(
                response.get("status")
                or (response.get("result") or {}).get("status")
                or ""
            )
            if status == "in_flight":
                raise SpawnError(
                    f"gateway reports a run already in flight for {run_id} — "
                    "not respawning (dedup); check the session before retry"
                )
            self.last_response = response
            return run_id
        finally:
            if msg_path:
                try:
                    os.unlink(msg_path)
                except OSError:
                    pass
            self.pool.release(run_id)
