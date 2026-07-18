# §88 check 1 — valid T2 envelope accepted (raw evidence)

- Date: 2026-07-18 (PDT); actor: A (bootstrap agent, sandbox host)
- Command: `python3 control/scripts/task_create.py projects/PROJECT-000/dryrun/envelope-check1-valid-t2.yaml`
- Stdout: `TASK-001`
- Exit code: 0
- Files produced by the tool (uncommitted at run time, committed in this change):
  - `projects/PROJECT-000/episodes/TASK-001/task.yaml` — envelope + allocated `task_id: TASK-001`
  - `projects/PROJECT-000/episodes/TASK-001/state.yaml` — `state: INTAKE`, history `NONE → INTAKE` at `2026-07-18T17:13:30Z`, evidence `task-create from envelope-check1-valid-t2.yaml`
- Branch: `dispatch/TASK-001` (per runbook row 1)
- Result: **PASS** — valid T2 envelope accepted; TASK-### allocated by the tool
  (id absent from the fixture per §82.1); task.yaml + state.yaml written.

Environment note: sandbox exec preflight refused chained `python | tee`
invocations; the tool was run as a direct single command and output recorded
verbatim above. No effect on the checked property.
