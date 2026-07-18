# §88 check 12 — breaker halts BLOCKED, no retry loop (raw evidence)

- Date: 2026-07-18 (PDT); actor: A; RUNBOOK-B7.2 row 12
- Task: TASK-002 (fixture `envelope-check12-breaker.yaml`,
  `tool_call_limit: 1`, tier T2), created by `task_create.py` (exit 0)

## Mechanism gap found first (friction → fix PR #65)

The §82.3 breaker did not exist: nothing counted tool actions against
`tool_call_limit`, and `effective_caps` ignored tighter envelope budgets
for T1/T2 (the fixture's cap of 1 silently became the tier's 100). Both
fixed in PR #65 (`record_action()`, envelope-tightened caps; unit tests).
This run used the fixed module (staged at /tmp for the run — the episode
branch carries no control-plane changes; sha256 7cd49b90d1febb41 printed
for provenance).

## Run (verbatim)

    effective caps (wall, tools): (30, 1)
    action #1 allowed, count=1
    action #2 tripped breaker: breaker: tool_call_limit 1 exceeded at action #2 — task BLOCKED (ESC-TASK-002.md)
    state: BLOCKED; ESC exists: True
    action #3 refused: task is BLOCKED; no further actions (§82.3 — resolve the escalation first)
    dispatch refused: task is BLOCKED; resolve the escalation first
    action events logged: 2 (breach action retained as evidence)
    RESULT: PASS

## Checked properties

| Property | Evidence |
|---|---|
| Second tool action trips the cap | breach at action #2 exactly (cap 1 honored via envelope-tightened caps: (30, 1), not tier (120, 100)) |
| State BLOCKED | state.yaml `state: BLOCKED`; transition committed with ESC filename as evidence |
| ESC evidence | `ESC-TASK-002.md` (front-mattered escalation record, reason `tool_call_limit 1 exceeded (action #2)`) |
| No retry loop | action #3 refused by the BLOCKED guard; `dispatch()` refused; log shows exactly 2 action events — the refused action never landed |
| Breach action retained | the tripping action is IN the log (evidence, not silently dropped) |

- Result: **PASS** — on the fixed mechanism, with the pre-fix gap recorded
  as B7.4 friction (runbook v1.6, PR #65).
