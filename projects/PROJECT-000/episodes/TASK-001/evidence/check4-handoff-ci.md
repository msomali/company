# §88 check 4 — handoff CI blocks bad front matter (raw evidence)

- Date: 2026-07-18 (PDT); actor: A (SDE work via bootstrap session, §86-C6)
- Vehicle: SDE work PR #53 (`sde/TASK-001-slugify`) — TASK-001 deliverable
  (`src/slugify.py`, `tests/test_slugify.py`, implementation note; 516 tests
  passing locally)

## Red leg (deliberate defect)

- Commit `b3a22a2`: implementation note front matter deliberately missing
  the required `updated` field.
- CI `lint` run: **fail** —
  https://github.com/msomali/company/actions/runs/29654736878/job/88106942719
- CI log line (verbatim):

      FAIL projects/PROJECT-000/notes/slugify-implementation.md: (root): 'updated' is a required property
      frontmatter-lint: 1 violation(s)

- Same defect reproduced locally pre-push (frontmatter_lint.py exit 1).

## Green leg (fix)

- Fix commit: adds `updated: "2026-07-18"` — one-line change.
- CI `lint` run: **pass** —
  https://github.com/msomali/company/actions/runs/29654775434/job/88107040717
- gitleaks + handoff green on both pushes.

- Result: **PASS** — handoff CI mechanically blocks an artifact missing a
  required front-matter field and passes once fixed; both runs linked above.
