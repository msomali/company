"""Tests for session_backend.py (activation item 1) — fake runner only.

What is unit-testable here (sandbox has no gateway/CLI, and the real code
runs in the dispatcher host process anyway): argv/env construction, token
pre-flight, run-id minting, JSON/exit handling, secret scrubbing, slot cap.
Live gateway behavior (connect/pairing, real fallback under rate limits,
--timeout semantics) is owner-observed per the dispatcher-install addendum.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import session_backend as sb  # noqa: E402

POLICIES = """\
mode: S
mode_s: {concurrency_cap: 3, prices_file: control/models/prices.yaml}
policies:
  reasoning-max: {primary: anthropic/claude-fable-5, fallback: anthropic/claude-opus-4-8}
  standard: {primary: openai/gpt-5.6-sol, fallback: openai/gpt-5.5}
agents: {PJM: standard, SDE: reasoning-max, SAT: standard}
"""

PROMPT = (
    "Constitution digest: company/digest-v1.1.md (v1.1, binding).\n\n"
    "## Task envelope\n\n```yaml\ntask_id: TASK-004\nproject_id: PROJECT-000\n"
    "assigned_role: SDE\n```\n"
)

# Fake fixture value — must LOOK token-like so the scrub test is honest;
# never a real credential (values never appear in this repo, BA-3).
TOKEN = "tok-sekrit-1234567890"  # gitleaks:allow
OK_JSON = '{"payloads": [{"text": "done"}], "meta": {"durationMs": 1200}}'


class FakeRunner:
    def __init__(self, rc=0, out=OK_JSON, err=""):
        self.rc, self.out, self.err = rc, out, err
        self.calls = []
        self.message_bodies = []

    def __call__(self, argv, env, timeout_s):
        self.calls.append({"argv": list(argv), "env": dict(env), "timeout": timeout_s})
        i = argv.index("--message-file")
        path = Path(argv[i + 1])
        assert path.is_file(), "message file must exist while the CLI runs"
        self.message_bodies.append(path.read_text(encoding="utf-8"))
        return self.rc, self.out, self.err


def make_backend(tmp_path, runner=None, env=..., **kw):
    pol = tmp_path / "policies.yaml"
    pol.write_text(POLICIES)
    if env is ...:
        env = {"OPENCLAW_GATEWAY_TOKEN": TOKEN, "PATH": "/usr/bin", "HOME": "/srv/company"}
    return sb.OpenClawSessionBackend(
        policies_path=pol, runner=runner or FakeRunner(), env=env, **kw
    )


def test_spawn_happy_path_argv_env_and_run_id(tmp_path):
    runner = FakeRunner()
    b = make_backend(tmp_path, runner=runner)
    run_id = b.spawn(agent_id="sde", prompt=PROMPT)

    assert re.fullmatch(
        r"agent:sde:task-004-\d{8}t\d{6}z-[0-9a-f]{6}", run_id
    ), run_id
    call = runner.calls[0]
    argv = call["argv"]
    assert argv[0:2] == ["openclaw", "agent"]
    assert argv[argv.index("--agent") + 1] == "sde"
    assert argv[argv.index("--session-key") + 1] == run_id
    assert "--json" in argv
    assert argv[argv.index("--timeout") + 1] == "3600"
    # no per-run model override — policy lives in gateway agents.list
    assert "--model" not in argv
    # env: token passed through, URL defaulted; grace on the hard timeout
    assert call["env"]["OPENCLAW_GATEWAY_TOKEN"] == TOKEN
    assert call["env"]["OPENCLAW_GATEWAY_URL"] == "ws://127.0.0.1:18789"
    assert call["timeout"] == 3600 + 120
    # the prompt travelled via the message file, then was cleaned up
    assert runner.message_bodies == [PROMPT]
    msg_path = Path(argv[argv.index("--message-file") + 1])
    assert not msg_path.exists()
    assert b.last_response["meta"]["durationMs"] == 1200


def test_timeout_seconds_maps_to_cli_flag(tmp_path):
    runner = FakeRunner()
    b = make_backend(tmp_path, runner=runner, timeout_seconds=1800)
    b.spawn(agent_id="sde", prompt=PROMPT)
    argv = runner.calls[0]["argv"]
    assert argv[argv.index("--timeout") + 1] == "1800"
    assert runner.calls[0]["timeout"] == 1920


def test_env_url_override_wins_over_default(tmp_path):
    runner = FakeRunner()
    b = make_backend(
        tmp_path, runner=runner,
        env={"OPENCLAW_GATEWAY_TOKEN": TOKEN, "OPENCLAW_GATEWAY_URL": "ws://127.0.0.1:19001"},
    )
    b.spawn(agent_id="sde", prompt=PROMPT)
    assert runner.calls[0]["env"]["OPENCLAW_GATEWAY_URL"] == "ws://127.0.0.1:19001"


def test_unknown_agent_refused_before_any_gateway_contact(tmp_path):
    runner = FakeRunner()
    b = make_backend(tmp_path, runner=runner)
    with pytest.raises(sb.SpawnRefused, match="unknown agent id 'intruder'"):
        b.spawn(agent_id="intruder", prompt=PROMPT)
    assert runner.calls == []


def test_missing_token_refused_and_names_the_env_file(tmp_path):
    runner = FakeRunner()
    b = make_backend(tmp_path, runner=runner, env={"PATH": "/usr/bin"})
    with pytest.raises(sb.SpawnRefused) as exc:
        b.spawn(agent_id="sde", prompt=PROMPT)
    assert "OPENCLAW_GATEWAY_TOKEN" in str(exc.value)
    assert "dispatcher.env" in str(exc.value)
    assert runner.calls == []


def test_nonzero_exit_raises_with_scrubbed_stderr(tmp_path):
    runner = FakeRunner(rc=1, out="", err=f"auth failed for token {TOKEN} at gateway")
    b = make_backend(tmp_path, runner=runner)
    with pytest.raises(sb.SpawnError) as exc:
        b.spawn(agent_id="sde", prompt=PROMPT)
    msg = str(exc.value)
    assert "exited 1" in msg
    assert TOKEN not in msg           # the load-bearing custody property
    assert "***" in msg
    assert b.pool.active == set()     # slot released on failure


def test_unparseable_json_raises_spawn_error(tmp_path):
    b = make_backend(tmp_path, runner=FakeRunner(out="not json at all"))
    with pytest.raises(sb.SpawnError, match="unparseable --json output"):
        b.spawn(agent_id="sde", prompt=PROMPT)


def test_in_flight_dedup_is_an_error_not_a_respawn(tmp_path):
    b = make_backend(tmp_path, runner=FakeRunner(out='{"status": "in_flight"}'))
    with pytest.raises(sb.SpawnError, match="in flight"):
        b.spawn(agent_id="sde", prompt=PROMPT)


def test_concurrency_cap_refuses_at_cap_and_recovers_on_release(tmp_path):
    runner = FakeRunner()
    b = make_backend(tmp_path, runner=runner)
    for held in ("t1", "t2", "t3"):
        assert b.pool.request(held)
    with pytest.raises(sb.SpawnRefused, match="concurrency cap 3"):
        b.spawn(agent_id="sde", prompt=PROMPT)
    assert runner.calls == []
    # refusal leaves NO queue residue — otherwise a later release() grants a
    # phantom slot that is never released (leak found by this test)
    assert not b.pool.queue
    b.pool.release("t1")
    assert b.spawn(agent_id="sde", prompt=PROMPT).startswith("agent:sde:task-004-")
    assert b.pool.active == {"t2", "t3"}    # own slot released after the turn


def test_prompt_without_task_id_gets_adhoc_run_id(tmp_path):
    b = make_backend(tmp_path)
    run_id = b.spawn(agent_id="pjm", prompt="no envelope here")
    assert re.fullmatch(r"agent:pjm:adhoc-\d{8}t\d{6}z-[0-9a-f]{6}", run_id)


def test_slot_released_after_successful_spawn(tmp_path):
    b = make_backend(tmp_path)
    b.spawn(agent_id="sde", prompt=PROMPT)
    assert b.pool.active == set()


def test_missing_cli_binary_is_a_prerequisite_refusal(tmp_path):
    """default_runner: absent binary → SpawnRefused naming the install SOP
    (owner requirement A — the CLI-location issue is a PREREQUISITE)."""
    with pytest.raises(sb.SpawnRefused, match="dispatcher-install"):
        sb.default_runner(
            ["/nonexistent/openclaw", "agent"], {"PATH": "/nonexistent"}, 5
        )
