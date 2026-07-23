#!/usr/bin/env python3
"""Generate the gateway ``agents.list`` snippet from policies.yaml.

Activation item 1 companion: the 13 role agents are defined in the OpenClaw
gateway config (host, outside this repo — BA-1), and their model
primaries/fallbacks MUST mirror control/models/policies.yaml or MODEL-001/002
silently drift. Host config has no CI lint, so the emitted provenance header
(source commit + DO-NOT-HAND-EDIT) is the only drift defense (owner
requirement, answer 4, 2026-07-21): regenerate after ANY policies.yaml
change; never hand-edit the applied block.

Why fallbacks are explicit per agent: ``agents.list[].model`` without its own
``fallbacks`` is STRICT — no fallback at all (docs concepts/model-failover).
The whole point of the generated chain is that a rate-limited primary fails
over inside the runtime, per policy pairs already evaluated under MODEL-002.

Output is JSON5 (openclaw.json is JSON5 — comments are legal), to stdout or
``--out``. ONE artifact, applied to TWO seats (owner act, activation day;
control/sops/dispatcher-install.md addendum):

1. **Gateway seat (execution):** merged into the gateway user's
   ``~/.openclaw/openclaw.json`` — workspaces, models, containment.
2. **Dispatcher seat (id resolution):** installed VERBATIM as
   ``/etc/company/openclaw-dispatcher.json`` with
   ``OPENCLAW_CONFIG_PATH`` pointing at it. The CLI validates ``--agent``
   against the INVOKING USER's config before contacting the gateway
   (agent-via-gateway.ts — proven by the 2026-07-21 first-live-spawn
   failure: the dispatcher's fresh default config knew only ``main``, so
   every spawn refused with "Unknown agent id"). Client-side, workspace
   paths are inert — only the ids resolve.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_PATH = REPO_ROOT / "control" / "models" / "policies.yaml"


class ConfigGenError(RuntimeError):
    pass


def _head_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def generate(policies_path: Path, commit: str, today: str) -> str:
    policies = yaml.safe_load(policies_path.read_text(encoding="utf-8")) or {}
    pmap = policies.get("policies") or {}
    agents = policies.get("agents") or {}
    if not agents:
        raise ConfigGenError(f"{policies_path}: no agents mapping")
    entries = []
    for code, policy_name in agents.items():  # preserves policies.yaml order
        pol = pmap.get(policy_name)
        if not isinstance(pol, dict) or "primary" not in pol or "fallback" not in pol:
            raise ConfigGenError(
                f"{policies_path}: agent {code} -> policy {policy_name!r} "
                "missing or lacks primary/fallback"
            )
        entries.append({
            "id": code.lower(),
            "workspace": f"/srv/company-agents/{code.lower()}",
            "model": {
                "primary": pol["primary"],
                "fallbacks": [pol["fallback"]],
            },
        })
    header = (
        "// GENERATED — DO NOT HAND-EDIT. Host config has no CI lint; this "
        "header is the only drift defense.\n"
        f"// source: control/models/policies.yaml @ {commit}\n"
        f"// generated: {today} by control/scripts/agents_config_gen.py\n"
        "// apply TWICE (dispatcher-install.md addendum): (1) merge "
        "agents.list into the gateway user's ~/.openclaw/openclaw.json "
        "(execution seat); (2) install this file VERBATIM as "
        "/etc/company/openclaw-dispatcher.json + OPENCLAW_CONFIG_PATH in "
        "dispatcher.env (dispatcher seat — the CLI resolves --agent ids "
        "from the invoking user's config, not the gateway's).\n"
        "// workspace: each dir must contain that role's AGENTS.md from "
        "control/manifests/_generated/<ROLE>/ (paths adjustable; ids are "
        "not — spawn(agent_id=role.lower())).\n"
        "// workspace root: /srv/company-agents — dispatcher-READABLE per the "
        "ADR-B006 delivery path; ~/company-agents (/home) retired by the "
        "2026-07-22 migration (ProtectHome ruling: the dispatcher never "
        "traverses /home/mr-robot; harvest reads the workspace).\n"
        "// fallbacks are explicit per agent: agents.list[].model without "
        "fallbacks is STRICT (docs concepts/model-failover).\n"
        "// regenerate after ANY policies.yaml change.\n"
    )
    return header + json.dumps({"agents": {"list": entries}}, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="gateway agents.list snippet from policies.yaml"
    )
    ap.add_argument("--policies", type=Path, default=POLICIES_PATH)
    ap.add_argument("--commit", help="source commit for the provenance header "
                                     "(default: git HEAD short)")
    ap.add_argument("--out", type=Path, help="write here instead of stdout")
    args = ap.parse_args(argv)
    commit = args.commit or _head_commit(args.policies.resolve().parent)
    today = datetime.date.today().isoformat()
    try:
        text = generate(args.policies, commit, today)
    except ConfigGenError as exc:
        print(f"agents-config-gen: {exc}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"agents-config-gen: wrote {args.out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
