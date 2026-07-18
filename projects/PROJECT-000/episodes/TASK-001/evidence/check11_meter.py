#!/usr/bin/env python3
"""§88 check 11 — metering leg: record TASK-001 model usage into the episode
(usage.yaml + log.jsonl model_usage events), priced via prices.yaml.

Mode S (ADR-B003) meters ESTIMATES. Under Gate 0 P2 option (b), TASK-001's
model work (SDE implementation, SAT review) ran through the bootstrap
session (§86-C6 attribution), so no per-call provider counts exist. Token
figures below are ESTIMATES DERIVED FROM COMMITTED ARTIFACT SIZES at
~4 chars/token, the standard rough ratio — basis documented per call and
reproducible from the repo:

  SDE call  input  = check-3 captured dispatch prompt (the actual prompt)
            output = src/slugify.py + tests/test_slugify.py + implementation
                     note (the actual deliverable bytes)
  SAT call  input  = the same deliverable bytes (material under review)
                     + the dispatch prompt (context)
            output = SAT cycle-1 (1874 B) + cycle-2 (1587 B) review bodies
                     (lengths fetched via GitHub API 2026-07-18)

Model: anthropic/claude-fable-5 (the session model; priced in prices.yaml).
Per-agent attribution: call order + this doc (SDE first, SAT second) — the
usage record itself has no agent field; recorded as friction.

Also exercises the §81.3 ceiling guard (envelope model_cost_limit_usd: 5.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

EVIDENCE_DIR = Path(__file__).resolve().parent
TASK_DIR = EVIDENCE_DIR.parent
REPO_ROOT = EVIDENCE_DIR.parents[4]
sys.path.insert(0, str(REPO_ROOT / "control" / "scripts"))
import metering as mt  # noqa: E402

CHARS_PER_TOKEN = 4
SAT_REVIEW_BYTES = 1874 + 1587  # comment bodies 5012331464 + 5012336995


def toks(nbytes: int) -> int:
    return max(1, round(nbytes / CHARS_PER_TOKEN))


def main() -> int:
    prompt = (EVIDENCE_DIR / "check3-dispatch-prompt.txt").stat().st_size
    deliverable = sum(
        (REPO_ROOT / p).stat().st_size
        for p in (
            "projects/PROJECT-000/src/slugify.py",
            "projects/PROJECT-000/tests/test_slugify.py",
            "projects/PROJECT-000/notes/slugify-implementation.md",
        )
    )
    calls = [
        ("SDE", toks(prompt), toks(deliverable)),
        ("SAT", toks(deliverable + prompt), toks(SAT_REVIEW_BYTES)),
    ]

    meter = mt.Meter()  # staleness guard: refuses prices older than 90 days
    print(f"prices as_of {meter.as_of} (staleness guard passed)")
    for agent, t_in, t_out in calls:
        usage = meter.record_usage(
            TASK_DIR, model="anthropic/claude-fable-5",
            input_tokens=t_in, output_tokens=t_out,
        )
        print(f"metered [{agent}] in={t_in} out={t_out} "
              f"running_cost={usage['total_estimated_cost_usd']}")

    meter.enforce_ceiling(TASK_DIR)  # raises BudgetExceeded on breach
    final = yaml.safe_load((TASK_DIR / "usage.yaml").read_text())
    print(f"usage.yaml: {final}")
    ceiling = yaml.safe_load((TASK_DIR / "task.yaml").read_text())[
        "budgets"]["model_cost_limit_usd"]
    print(f"ceiling check: {final['total_estimated_cost_usd']} <= {ceiling} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
