---
memory_id: MEM-ORG-0001
namespace: org
type: observed
subject: Shared-worktree commits require hunk-level verification (lesson L-001)
scope: all agents committing from a shared working tree
source: "PR #16 §5; commits 67ad1502, 4c8a8e4; L-001 audit 2026-07-17"
creator: bootstrap agent (agenticfoundrybot)
confidence: verified
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
expires: null
retention: review at §87 phase declaration; keep while any shared worktree exists
supersedes: null
superseded_by: null
related: ["BOOTSTRAP-PLAN.md", "control/sops/incident.md"]
---

# Shared-worktree commits require hunk-level verification

Observed failure (bootstrap, B3.2→B0.4 window): a commit swept up a plan tick
authored by someone else's uncommitted edit in the shared worktree, while the
commit message claimed ticks that were never staged. The plan diverged from
reality in both directions and review of `--stat` (file list) missed it.

Rules extracted (in force since 2026-07-17):

1. Never stage with `git add -A` in a shared worktree — add explicit paths.
2. Before any commit touching a register or plan file, read the staged hunks
   (`git diff --cached -- <file>`), not just the file list.
3. A tick's artifact must exist on main before the tick lands (no
   self-referential ticks).

Evidence: PR #16 provenance note and the L-001 audit that restored the B2.1
and B3.1 ticks after verifying their artifacts on main.
