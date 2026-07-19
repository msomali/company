# §88 check 2 — missing acceptance_criteria rejected pre-model (raw evidence)

- Date: 2026-07-18 (PDT); actor: A (bootstrap agent, sandbox host)
- Command: `python3 control/scripts/task_create.py projects/PROJECT-000/dryrun/envelope-check2-invalid.yaml`
- Stdout/stderr (verbatim):

      task-create: REJECTED
        FAIL (root): 'acceptance_criteria' is a required property

- Exit code: **2** (≠ 0, per §82.1 rejection contract)
- Nothing written:
  - `projects/PROJECT-000/episodes/` contains only `TASK-001` (pre-existing);
    no `TASK-002` directory created
  - `git status --porcelain` empty immediately after the run
- No model call — structural: `grep -cE 'import (openai|anthropic|requests|httpx|urllib)'`
  on `task_create.py` → 0 matches; the module imports no model or HTTP client
  by construction.
- Result: **PASS** — invalid envelope rejected pre-model, failing field named,
  exit nonzero, zero side effects.
