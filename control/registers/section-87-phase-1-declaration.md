# §87 Phase 1 Declaration — Version 2.1 Minimum Enforceable Operating System

**Declared by:** bootstrap agent (agenticfoundrybot, BA-1) on the human owner's
authorization (msomali, 2026-07-19).
**Repository:** `msomali/company` (control repo).
**Plan row:** Bootstrap Annex BA-6 / BOOTSTRAP-PLAN **B7.4**. This artifact is the
terminal output of the bootstrap build.

## 1. Declaration

Version 2.1 **Phase 1 — Minimum Enforceable Operating System (§73)** is
**COMPLETE** per §87, on the evidence recorded below. §87 is an iff over five
conditions (a)–(e); each is met and independently verifiable on `main`. Per §87,
*"No prose, intention, or partial script counts"* — every element below points to
a merged mechanism or a committed artifact, not an intention.

## 2. §87 Definition of Done — condition-by-condition evidence

**(a) The §85 evidence checklist is committed — and fully closed.**
`control/sops/hardening-evidence.md`: **9/9 rows `[x]`, zero open**. The final row,
row 4 (per-agent containers / **egress allowlist**), closed via **PR #76** (merged;
gate `gates/GATE-HUMAN-PR76-14bd3ad2.yaml`): DOCKER-USER iptables bounded egress
**applied** (DNS + established/related + HTTPS/443 from 172.17.0.0/16, log+drop all
else), **tested** (GitHub/443 → HTTP 200; ports 9999 and 80 dropped/timed-out),
**persisted** (iptables-persistent, `/etc/iptables/rules.v4`, survives reboot);
host evidence `/var/company/hardening/row4-egress-evidence.txt`. Footer attests
"all §85 hardening rows are now closed." Host facts owner-attested; dual-control
review recorded (approving review by agenticfoundrybot).

**(b) Every Phase-1 §78 row has its mechanism merged, configured, and referenced.**
The row-by-row mechanism→PR index is `BOOTSTRAP-PLAN.md` (BA-6), reconciled in §5.
Key Phase-1 mechanisms on `main`:

| Mechanism (§78 / §82–84) | Location | Landed |
|---|---|---|
| Branch protection + CODEOWNERS + required checks (policy set v0, row 30) | `control/sops/branch-protection.md`, `CODEOWNERS` | PR #4/#5/#7 |
| CI: frontmatter-lint, handoff-check, secret-scan, eval-runner | `.github/workflows/`, `control/scripts/*_lint.py` | PR #8 (required PR #9) |
| Model-routing proxy (Mode P **dormant**, ADR-B003) | `control/models/proxy/` | PR #10 |
| Manifest generator + 13 manifests (generated, **not activated**) | `control/scripts/manifest_generator.py`, `control/manifests/` | PR #11/#12 |
| `task-create` + `schemas/task.json` | `control/scripts/task_create.py` | PR #13 |
| Dispatcher (§82) incl. §82.3 breaker + §15 wall-clock cap | `control/scripts/dispatcher.py` | PR #14/#15 (+ #71) |
| Dispatcher systemd unit (`dispatcher` user) | `control/sops/systemd-company-dispatcher.service` | PR #17/#18/#20 |
| Episode collector + kill switch | `control/scripts/episode_collector.py`, `kill_switch.sh` | PR #19 |
| Eval runner + golden tasks (§84); seeded-failure blocks | `control/scripts/eval_runner.py`, `control/evals/` | PR #22 |
| Gate-writer (row 4) emits `gates/GATE-*.yaml` on merge | `control/scripts/gate_writer.py`, `.github/workflows/gate-writer.yml` | PR #23/#24/#25 |
| `/memory` tree + gated write path + purge (§83) | `memory/`, `control/scripts/memory_{lint,purge}.py` | PR #27 |
| SOPs (§68–72) | `control/sops/` | PR #29 |
| Weekly metrics (row 26) | `control/scripts/metrics_weekly.py` | PR #31 |

Conditional/dormant, correctly not built: **B2.2** (Mode P reactivation) is
**N/A-dormant** — Mode S is ACTIVE (ADR-B003); the proxy config exists but is
dormant, reactivation requires an owner ADR.

**(c) The §86 register carries human-owner approval.**
`control/registers/section-51-owner-and-section-86-signature.md` — signed
**msomali 2026-07-16**; compensating controls **C1–C7 all APPROVED**; quarterly
review 2026-10-16 (C5 also on any provider-policy change). Fills the v1 §51 owner
specification by reference.

**(d) The §88 dry run passes in full (14/14).**
Acceptance episode `projects/PROJECT-000/episodes/TASK-001/` on `main` (**PR #58**,
merge `e5d18e4`), with the check-12 breaker episode
`projects/PROJECT-000/episodes/TASK-002/`. Manifest `--check` green: **32 files,
all sha256-hashed, `complete: true`, `final_state: CLOSED`**. Per-check evidence in
§3. Gate-writer emitted `gates/GATE-SAT-PR58-e5d18e4a.yaml` on the episode merge.

**(e) A first weekly metrics artifact has been generated (row 26).**
`company/metrics/METRICS-2026-W29.md` (status **APPROVED**), produced by
`control/scripts/metrics_weekly.py` (**PR #31**); window 2026-07-11 → 2026-07-17.

## 3. §88 Dry-Run Result — 14 / 14 PASS

Evidence paths are under `projects/PROJECT-000/` on `main`.

| # | §88 check | Verdict | Evidence |
|---|---|---|---|
| 1 | task-create accepts valid T2 (writes task/state) | PASS | `episodes/TASK-001/evidence/check1-task-create.md` |
| 2 | rejects missing acceptance criteria **before any model call** | PASS | `.../check2-rejection.md` |
| 3 | dispatch prompt carries digest + envelope + artifact links | PASS | `.../check3-dispatch-prompt-contract.md` (+ prompt/results) |
| 4 | handoff CI blocks bad front matter, passes once fixed | PASS | `.../check4-handoff-ci.md` |
| 5 | SAT two-cycle review (request→revise→approve; owner confirm) | PASS | `.../check5-sat-two-cycle.md` |
| 6 | separation of duties (author-review + no-review both blocked) | PASS | `.../check6-separation-of-duties.md` |
| 7 | merge emits `gates/GATE-SAT-*.yaml` | PASS | `gates/GATE-SAT-PR53-e90c735e.yaml` (first non-HUMAN record) |
| 8 | human approvals captured into gate records | PASS | `.../check8-approvals-capture.md`, `check8-state-walk.md` |
| 9 | release merge blocked without `APPROVE`, succeeds with it | PASS | `.../check9-release-gate.md` (verbatim **405** blocked leg; merge `f9bb463b`) |
| 10 | episode completeness (§9 checklist) | PASS | `.../check10-episode-completeness.md`; `manifest.yaml` |
| 11 | cost report — per-agent metered usage | PASS | `.../check11-cost-report.md`; `usage.yaml` |
| 12 | breaker halts BLOCKED with evidence, no retry loop | PASS | `episodes/TASK-002/evidence/check12-breaker.md`; `ESC-TASK-002.md` |
| 13 | kill-switch pause/resume re-dispatch from `state.yaml` | PASS | `.../check13-killswitch-redispatch.md`; `check13-owner-pause-capture.txt` |
| 14 | failing golden task blocked by eval CI; fixed→merge+tag | PASS | `.../check14-eval-ci-release.md`; merge `f432528`; tag `evals-v1.0` |

## 4. B7.4 Friction Backlog — carried forward with dispositions

§88 mandate: *"Convert every friction point discovered into either a §78 mechanism
fix or a new eval case before declaring completion."* The consolidated 16-item
dry-run friction list (full text in `projects/PROJECT-000/dryrun/RUNBOOK-B7.2.md`
and the check-14 evidence) is dispositioned below. **No item is a pre-§87 blocker**
(owner ruling 2026-07-19); the safety-critical findings are resolved and on `main`.

**Resolved in-run (mechanism fixed / rule recorded on `main`):**
- 2 — §86-C6 claim channel dead for bot PRs → MEM-ORG-0004 + handoff-check enforcement.
- 4 — B7.3 had no authored procedure → RUNBOOK-B7.3 authored.
- 6 — metrics scanned the wrong episode path → fixed (`projects/*/episodes/`).
- 7 — usage.yaml format divergence → fixed + calls-int regression test.
- 10 — **wall-clock breaker** (safety, §15) → landed **PR #71** (`record_action` wall cap).
- 11 — merge-race orphan → **MEM-ORG-0005** (verify `is-ancestor` after every merge).
- 12 — stacked-PR orphan → **MEM-ORG-0005** (no-stacking rule).
- 13 — **§82.3 breaker did not exist** (safety) → `Dispatcher.record_action()` built.
- 14 — `effective_caps` ignored tighter envelope budgets → fixed (tighter always wins).

**Priority backlog (first post-§87 build item — data-loss class):**
- 9 — **W29 weekly-metrics overwrite guard:** `metrics_weekly` must REFUSE to
  overwrite a committed report unless loudly forced (explicit flag + printed
  warning naming the file). Owner-approved work item; lands soon, not buried.

**Activation-era (deferred to when agents actually run):**
- 1 — real `sessions_spawn` wiring (the dry run used the recorded-prompt backend, Gate 0 P2(b)).
- 3 — extend `claimed_role()` to scan issue comments so check-5/check-7 compose.
- 8 — per-agent token attribution on `record_usage`.
- 15 — gate-writer replay `--force-with-lease` on an existing gate branch.

**Procedure note (recorded, no code change):**
- 5 — a release PR must not be zero-delta vs `main`; cut `release` one commit
  behind, or promote via an rc branch.

**Intentional — do NOT remove (doc item):**
- 16 — the **lint↔evals coupling** is intentional. The `evals` path filter
  (`control/evals/**` …) is the P3 mitigation that stops a required eval check from
  hanging PRs that don't touch eval paths; the `lint`-side full-suite guard
  (`test_eval_runner.py::test_full_suite_behaves_as_expected`) keeps eval
  regressions caught on **every** PR. The two are counterparts — **removing either
  regresses**. Recorded in the check-14 evidence; owner ruling 2026-07-19.

## 5. BOOTSTRAP-PLAN reconciliation

At declaration time the single-source-of-truth plan (BA-5.5) lagged reality: five
rows were complete and merged on `main` but left unticked — the mirror image of the
ticks-without-artifacts failure (L-001 / MEM-ORG-0001). This PR reconciles them,
each with landing evidence:

- **B6.2** SOPs finalized — PR #29.
- **B6.3** weekly metrics + first report — PR #31.
- **B7.1** PROJECT-000 charter signed — PR #49 (status APPROVED).
- **B7.2** dry run checks 1–5, 7, 10–14 — PR #58 (episode on `main`).
- **B7.3** dry run checks 6, 8, 9 — PR #58 (episode on `main`).
- **B7.4** Phase 1 declared per §87; friction converted — **this PR**.

## 6. Activation boundary (mandatory statement)

**Declaring Phase 1 does NOT activate any agent.** Agent activation is a
**separate, post-declaration human act** per **BA-2.4** — a manifest's `status`
becomes `active` only by a deliberate owner action, never by this declaration and
never by an agent. **No manifest is activated by this artifact.** The entire §88
dry run ran with **no activated agent**: the recorded-prompt backend (Gate 0
P2(b)) captured the real dispatch prompt contract without spawning a live agent;
real `sessions_spawn` wiring is activation-era work (B7.4 item 1). Phase 1
"complete" means the **enforcement substrate** is built, exercised, and evidenced —
not that autonomous work has begun.

## 7. What remains after this declaration

- **B8.1** (owner act): revoke the bootstrap identity; rotate tokens.
- **Agent activation** for the first real project — a separate human act (BA-2.4),
  gated by the operator's decision, not by this declaration.
- **Priority backlog item 9** (W29 overwrite guard) — first post-§87 build item.
- **Phase 2 entry (§78):** requires Phase 1 complete (this) **plus at least one
  real project shipped through all gates**.

## 8. Bootstrap complete

The bootstrap build is **complete**. Every mechanism Version 2.1 Phase 1 requires
exists on `main`, is configured, is referenced from the control repo, and has been
exercised under the §88 dry run with committed evidence. This is the terminal
artifact of the build.

Effective on the human owner's review and merge of this PR (the declaration
reaching `main`); the subsequent B8.1 identity handoff is the owner's to run.

- **Bootstrap actor:** agenticfoundrybot (BA-1)
- **Authorizing owner:** msomali (§51 / §86)
- **Date:** 2026-07-19
