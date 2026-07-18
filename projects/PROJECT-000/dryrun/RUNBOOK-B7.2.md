---
artifact_id: projects/PROJECT-000/dryrun/RUNBOOK-B7.2.md
title: B7.2 dry-run runbook — §88 checks 1–5, 7, 10–14 (joint)
type: runbook
project: PROJECT-000
owner: bootstrap agent (agenticfoundrybot)
version: "1.4"
status: READY_FOR_REVIEW
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-18"
---

# B7.2 Dry-Run Runbook — §88 checks 1–5, 7, 10–14

Joint execution (BA-6 row B7.2); evidence target: episode package(s) under
`episodes/` reaching `main` by PR. Checks 6/8/9 are B7.3 (owner solo).

## Gate 0 — preconditions (BLOCKING, owner)

- **P1. Charter signature (B7.1).** **RESOLVED 2026-07-18** — charter
  signed and merged (PR #49): `status: APPROVED`, both approval fields
  `msomali 2026-07-18`, budget ceiling finalized at USD 50 (anomaly
  breaker).
- **P2. Check-3 backend decision.** The dispatcher refuses dispatch unless
  the role manifest is `active` (activation = human act, BA-2.4) and needs a
  session backend (`sessions_spawn` wiring is deliberately absent during
  bootstrap). Options:
  - **(a) Pilot activation:** owner flips `sde.yaml`/`sat.yaml` status to
    `active` for PROJECT-000 and we wire the minimal real backend — fullest
    §88.3 evidence; largest step.
  - **(b) Recorded-prompt backend:** run the dispatcher with the test
    backend on the host, capture the *actual generated prompt* (digest ref,
    envelope, artifact links) into the episode as evidence; §88.3's checked
    property is the prompt contents. Model calls for SDE/SAT work then run
    through this bootstrap session under the operative §86-C6 attribution.
  - Recommendation: **(b)** for B7.2, recording the delta as B7.4 friction
    ("real spawn wiring") — §87 completion judges mechanisms + prompt
    contract, and (b) proves both without an activation act mid-dry-run.
  - **DECIDED 2026-07-18 (owner):** option **(b)** — recorded-prompt
    backend. No manifest is pilot-activated during the dry run; activation
    stays a post-§88 human act per BA-2.4. The `sessions_spawn` wiring
    delta is logged as B7.4 friction (entry below).
- **P3. Evals-required toggle (checks 4/14).** `evals` is not a required
  status (path-filter hazard, PR #22 §5). For the dry-run window, §88.14's
  "blocked by eval CI" is cleanest if the owner temporarily adds `evals` to
  required checks, reverting after B7.3. Alternative: red-check + owner
  refuses merge (policy block, not mechanical). Owner's call; evidence notes
  which form ran.

## Fixtures (this PR)

- `envelope-check1-valid-t2.yaml` — valid T2 envelope (PJM → SDE, slugify
  per charter scope; budgets within ceiling, cost limit set).
- `envelope-check2-invalid.yaml` — same, minus `acceptance_criteria`
  (rejection expected **before any model call**; task-create imports no
  model client — structural).
- `envelope-check12-breaker.yaml` — `tool_call_limit: 1` breaker case.

## Execution order

| # | §88 check | Actor | Procedure → evidence |
|---|---|---|---|
| 1 | Valid T2 accepted | A (host: dispatcher user) | `task_create.py` on fixture 1 → TASK-### allocated, task.yaml + state.yaml (INTAKE) committed on `dispatch/TASK-###` → episode |
| 2 | Missing acceptance criteria rejected pre-model | A | `task_create.py` on fixture 2 → rejection listing the field; exit ≠ 0; no task dir created |
| 3 | Dispatch prompt contract | J (per P2) | dispatcher `dispatch()` → prompt captured; verify digest reference + envelope + artifact links present |
| 4 | Handoff CI blocks bad front matter | A | SDE work PR with one front-matter field deliberately missing → `lint` red; fix; green. Both runs linked in episode |
| 5 | SAT two-cycle review | J | SAT (bot, explicit role attribution, gate-record format) requests changes; SDE revises; SAT approve-recommend; owner required review confirms |
| 7 | Merge emits GATE-SAT-*.yaml | A (CI) | gate-writer on the merge; record shows SAT attribution + evidence links (first non-HUMAN gate record) |
| 10 | Episode completeness | A | `episode_collector.py` assemble + `--check` → §9 checklist green in manifest.yaml |
| 11 | Cost report | A | metering usage.yaml priced via prices.yaml; `metrics_weekly.py` shows the task's tokens/cost (per-agent usage) |
| 12 | Breaker halts BLOCKED | A | dispatch fixture 3; second tool action trips the cap → state BLOCKED + ESC evidence, no retry loop |
| 13 | Kill switch pause/resume mid-task | J | pause during an in-flight task (owner window per drilled SOP); resume → dispatcher re-dispatches from state.yaml and the task completes. Sever/freeze legs already evidenced 2026-07-17 (row 9); this adds the re-dispatch leg |
| 14 | Failing golden task blocks prompt-bundle PR; fixed → merge + release tag | J | PR touching `control/evals/**` with a failing case → eval CI red (per P3 form); fix; merge; owner tags release |

## §86-C6 claim channel (added 2026-07-18, check-7 hold; MEM-ORG-0004)

Bot-role PRs **MUST** carry the machine-readable gate-role claim — a
line-start `role: <ROLE>` — in the PR body (handoff template). Mandatory,
not optional: under ADR-B000 the author-bot cannot review its own PR, so
the approving-review-body claim channel is **structurally dead for all
bot-role gates**; the PR body is the only live channel gate-writer parses
when emitting the gate record on merge. Check-5-style gate-record comments
are review *evidence*, not a claim channel — the emitter never reads
comments. Enforced by handoff-check (fails role-prefixed branches without
the claim); the owner verifies claimed attribution at merge (C6 backstop).
Check 7's first run demonstrated the failure: emitted `GATE-HUMAN-PR53`
superseded by PR-body claim + workflow_dispatch replay → `GATE-SAT-PR53`.

## Rules in force during the run

- Every check's raw output lands in the episode package, not chat.
- Friction is recorded at the moment it appears (B7.4 input list at the
  bottom of the episode README) — no smoothing.
- Any check unpassable after two remediation attempts → ESC + stop (charter
  kill criterion 1).

## B7.4 friction list (live, appended during run)

- (pre-seeded; confirmed by owner P2 decision 2026-07-18) Real
  `sessions_spawn` wiring absent by design — check 3 ran on the
  recorded-prompt backend (P2 option b). Real spawn wiring is a post-§88
  activation-era work item.
- (check 7, 2026-07-18) Under ADR-B000 the approving-review-body claim
  channel is dead for every bot-role PR — the author-bot cannot review its
  own PR, so §86-C6 claims can only travel in the PR body. First check-7
  run emitted `GATE-HUMAN-PR53` for a SAT-gated PR. Permanent constraint:
  MEM-ORG-0004; enforcement added to handoff-check.
- (check 7, 2026-07-18) Check-5 evidence format (gate-record comments) and
  the check-7 emitter (review-body/PR-body parser) do not compose —
  comments are invisible to `claimed_role()`. Deferred activation-era
  hardening candidate: extend `claimed_role()` to scan issue comments so
  the two mechanisms compose mechanically.
- (check 8/9 setup, 2026-07-18) Plan row B7.3 (checks 6/8/9, owner-solo)
  existed with **no authored procedure anywhere in the repo** — same
  failure class as ticks-without-artifacts (L-001/MEM-ORG-0001): a plan
  row with no executable procedure. Caught by the owner when preparing
  checks 8/9 (after check 6's numbering jump). Remedied: RUNBOOK-B7.3.md
  authored from the implemented mechanisms (approvals.py, §51 register
  interim channel, state-machine prerequisites, release-branch setup).
- (check 9, 2026-07-18) Runbook step "release PR head `main`" was
  unexecutable: owner cut `release` at the `main` head, zero-delta PR
  refused by GitHub. Promotion rode `rc/TASK-001` with the release-notes
  artifact. Procedure note: cut `release` one commit behind, or always
  promote via an rc branch.
- (check 11, 2026-07-18) `metrics_weekly.collect_tasks` scanned only
  `<root>/episodes/` — a layout no project uses — so the cost report
  showed zeros against a metered episode. Fixed: scans
  `projects/<P>/episodes/` too.
- (check 11, 2026-07-18) usage.yaml format divergence: `metering.py`
  writes totals + `calls:` int; `metrics_weekly` (and its test fixture)
  expected a per-call list — iterating the int would crash. The modules
  were never integrated until §88.11. Fixed: totals format is read
  natively (record-time pricing respected); list form kept for compat;
  calls-int regression test added.
- (check 11, 2026-07-18) Per-agent usage gap: no mechanism records WHICH
  agent consumed tokens — `record_usage` has no agent field, so §88.11's
  "per-agent usage" is satisfied only by documented call order under
  P2(b). Activation-era fix candidate: `agent` param on `record_usage` +
  log event + usage.yaml per-agent rollup.
- (check 7 replay, 2026-07-18) gate-writer's replay cannot overwrite an
  existing `gate/pr-N` branch: the CI clone lacks a remote-tracking ref for
  it, so `--force-with-lease` rejects with "stale info" (run 29656689445 —
  record built correctly, publish failed). Workaround: operator deletes the
  stale branch (closing its gate PR unmerged) and re-dispatches; the fresh
  create then succeeds. Fix candidate (deferred): fetch the gate branch ref
  before pushing, or drop the lease on the replay path.
