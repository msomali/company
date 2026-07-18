---
artifact_id: projects/PROJECT-000/RELEASE-NOTES-TASK-001.md
title: TASK-001 release notes — slugify v1.0
type: release-notes
project: PROJECT-000
owner: human owner (release authority); drafted by bootstrap agent
version: "1.0"
status: RELEASE_CANDIDATE
sensitivity: internal
created: "2026-07-18"
updated: "2026-07-18"
---

# TASK-001 Release — slugify v1.0

Release artifact for §88 check 9 (PROJECT-000 synthetic dry run).

## Contents

- `src/slugify.py` — NFKD-fold slugifier (unicode folding, separator
  trimming, deterministic; known limit: non-decomposable scripts drop out,
  pinned by tests per SAT-53-F1).
- `tests/test_slugify.py` — 521 tests: edge cases, non-Latin pinning,
  fixed-seed property tests.

## Gate lineage (all records under projects/PROJECT-000/gates/)

| Gate | Record | Decision |
|---|---|---|
| SAT | GATE-TASK-001-SAT-1 | APPROVED (review 4729329698) |
| SSE | GATE-TASK-001-SSE-1 | APPROVED (same review) |
| DPC | GATE-TASK-001-DPC-1 | APPROVED (same review) |
| DCE | GATE-TASK-001-DCE-1 | APPROVED (review 4729371783) |
| PJM | GATE-TASK-001-PJM-1 | APPROVED (review 4729376823) |
| HUMAN | pending — issued on the release PR (§88.9 succeeds leg) |

Task state at release-PR open: `HUMAN_RELEASE_AUTHORIZATION`.

## Note on promotion shape

RUNBOOK-B7.3 step 3 said head `main`; the owner cut `release` at the
current `main` head, so a zero-delta PR was impossible. Promotion rides
this release-candidate branch (`rc/TASK-001`) carrying only this notes
artifact — recorded as procedure friction in the B7.4 list.
