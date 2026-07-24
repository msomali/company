---
artifact_id: control/adr/ADR-B007-task-lane-worktrees.md
title: ADR-B007 — Task-Lane Worktrees (Symmetric State Access, Main-Pinned Code Vintage)
type: adr
project: control
owner: human-owner
version: "1.0"
status: READY_FOR_REVIEW
sensitivity: internal
created: "2026-07-23"
updated: "2026-07-23"
approval: human-owner
---

# ADR-B007 — Task-Lane Worktrees

**Context.** The TASK-003 close walk (2026-07-23) exposed a structural
read/write asymmetry in every dispatcher state path. Reads —
`Dispatcher.task_dir()` and all its consumers (`--transition`,
`--dispatch-once`, `--harvest-once`, `--process-review`, the `--once`/
`--daemon` scan) — resolve `projects/<P>/episodes/<T>/...` against the
clone's **current checkout**. Writes go through `TaskBranchCommitter`, which
**switches the checkout** to `dispatch/TASK-###` and pushes. One working
tree is being asked to be two things at once:

- With the clone on `main` (Code-vintage rule 1, SOP), a task whose
  envelope/state live only on its dispatch lane is invisible to reads —
  the runtime answers **"no such task"**, or worse, reads stale
  merged-to-main state for a task whose lane has moved on.
- With the clone on the lane (so reads work), `control/scripts/` reverts to
  branch vintage (finding 1) — the close walk therefore had to **merge main
  into the episode lane** to get current tooling (`046fe2b`, `7074d0a`),
  history pollution the episode PR (#122 §3) then had to explain away.
- The initial lane commit at task creation has no sanctioned path at all
  (`task_create` writes the episode dir but commits nothing; TASK-003's
  envelope was relocated onto its lane by hand).

The asymmetry is the common root of three logged findings: branch-vintage
reversion (finding 1, 2026-07-23), the legacy-lane main-sync merges
(#122 §3), and the "no such task" refusal against branch-resident tasks.
Precedent already in the codebase: `GitHarvester` solved the identical
problem for the **delivery** lane with a temporary worktree ("the clone's
own checkout (state lane) is never disturbed" — harvest.py, PR #103). This
ADR applies the same mechanism to the state lane, symmetrically.

**Decision (PROPOSED).**

1. **The clone's checkout becomes code-only, pinned to main.** The
   dispatcher clone sits permanently on current `main`; no state operation
   ever switches it. Code-vintage rule 1 (SOP) reduces from
   "switch back before any command" to `git pull --ff-only` — there is no
   longer a wrong branch to be on.
2. **Each active task's lane is a persistent git worktree.**
   `dispatch/TASK-###` materializes at `.dispatch-worktrees/TASK-###`
   (same repository, own checkout, shared object store). New lanes are
   created from freshly fetched `origin/main` — the vintage property
   pinned by `tests/test_branch_vintage.py` carries over by construction;
   existing lanes attach to their branch as-is. The delivery lane's
   `.delivery-worktrees` pattern, made persistent for the episode's life.
3. **Reads and writes both resolve through the lane.**
   `Dispatcher.task_dir()` returns the lane worktree path for the task;
   transitions, log appends, dispatch records, and harvest's episodic
   events read there, write there, commit there, and push from there.
   Same committer identity, same provenance rules, same branch namespace —
   only the tree moves. "No such task" then means the task does not exist
   on the lane OR main, never "you are on the wrong branch".
4. **The scan reports the union.** `--once`/`--daemon` read active lane
   worktrees as authoritative and the main tree for closed/merged
   episodes; a task present in both with divergent state reports the lane
   and WARNs — main is a deliberately lagging mirror (episodes land on
   main via PR at close; B4.3 design decision 2 unchanged).
5. **Lifecycle.** Lane worktree created at first lane write — or at
   creation via a new opt-in `task_create --commit-lane` (closes the
   manual-relocation gap); pruned in the close runbook after the episode
   PR merges (`git worktree remove` + `git worktree prune`). Crash
   leftovers are inspectable trees; removal follows inspection, mirroring
   the delivery-worktree SOP note.
6. **Hygiene.** `.dispatch-worktrees/` and `.delivery-worktrees/` enter
   `.gitignore` (committers add explicit paths, so this is
   belt-and-braces, not a correctness requirement).

**Custody implications.** None moved: same deploy key, same
committer/author identities, same `dispatch/TASK-###` push targets, no new
credential homes, kill-switch semantics unchanged (severing the deploy key
halts lane pushes regardless of tree layout). Worktrees are host-filesystem
structures under the existing clone root, readable by the same OS user.

**Rejected alternatives.**

- *Plumbing reads* (`git show branch:path` without a worktree): fixes only
  the read half — log.jsonl appends and YAML rewrites still need a
  materialized tree, leaving two access modes to drift apart.
- *Status quo + SOP discipline* ("switch, run, switch back"): procedural
  where structural is available — the same principle the owner ruled on for
  the #115 gate interlock; and it failed live within a day of being
  written down.
- *Merge main into lanes when tooling is needed*: pollutes the episode
  record with tooling merges; already had to be explained in #122 §3.
- *Second full clone for state*: double disk and fetch traffic, two object
  stores to drift, no isolation gain over worktrees (which share refs and
  objects atomically).

**What is accepted.** One repo checkout of disk per active lane (small,
bounded by the concurrency cap); the main tree is knowingly stale for
active tasks (the scan says which tree answered); `.git/worktrees` metadata
needs the prune step in the close runbook.

**Affected files (implementation, on acceptance).**
`control/scripts/dispatcher.py` (lane class owning root+commit+push;
TaskBranchCommitter's switch retires), `control/scripts/dispatcher_runtime.py`
(task_dir resolution + scan union), `control/scripts/task_create.py`
(`--commit-lane`), `.gitignore`, `control/sops/dispatcher-install.md`
(Code-vintage section simplifies; close runbook gains prune; stale-lane
inspection note), tests (vintage tests extended to the lane class; scan
union tests; creation-commit tests). Two implementation PRs: core lane
mechanism, then runtime/scan wiring + SOP.

**Decision record (ADR lifecycle).** Lifecycle state: **PROPOSED**,
2026-07-23 (this PR is the proposal; owner acceptance via review on this
head is the acceptance act, per the ADR-B006 precedent). Front-matter
`status` uses the artifact schema's vocabulary (`READY_FOR_REVIEW`), as
ADR-B006's decision record established; on acceptance it moves to
`APPROVED` with the acceptance rider.
