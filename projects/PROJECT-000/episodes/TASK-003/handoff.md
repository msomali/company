---
artifact_id: SDE-TASK-003-handoff
task_id: TASK-003
project_id: PROJECT-000
role: SDE
status: READY_FOR_REVIEW
version: 1.2.0
data_classification: internal
---

role: HUMAN

# Handoff — TASK-003: titlecase_id implementation

Note: this document has been re-headed to the ten canonical section titles
specified in the TASK-003 envelope (previously inferred from the digest's
"ten-item handoff package"); content is preserved from v1.0.0.

## 1. Requested deliverable

Implemented `titlecase_id(s)`, which converts a short title into a lowercase,
hyphen-joined identifier: ASCII letters lowercased, runs of non-alphanumeric
characters collapsed to single hyphens, no leading/trailing hyphens, and empty
or whitespace-only input yields the empty string. Deliverables were
restructured to the repo-relative paths required by the task envelope, and the
full test suite passes (24 tests + 2 doctests).

Artifacts and locations:
- `projects/PROJECT-000/src/titlecase_id.py` — implementation.
- `projects/PROJECT-000/tests/test_titlecase_id.py` — pytest suite.
- `handoff.md` (this document) — workspace root.

## 2. Source requirements and traceability

From TASK-003 (requested by PJM, tier T2, risk low, internal data):
- Empty and whitespace-only input returns empty string (test-proven).
- ASCII letters lowercased; runs of non-alphanumerics collapse to single
  hyphens (test-proven).
- No leading or trailing hyphens (test-proven).
- Deliverables at `projects/PROJECT-000/src/titlecase_id.py` and
  `projects/PROJECT-000/tests/test_titlecase_id.py`.
- `handoff.md` at workspace root with the ten canonical sections and a
  gate-claim line reading `role: HUMAN` (the claim names the reviewing gate
  per §86-C6; the human owner reviews this delivery, and the author-bot
  cannot review its own PR per ADR-B000).

Traceability: each artifact carries front-matter metadata with
`task_id: TASK-003`, `project_id: PROJECT-000`, and an `artifact_id`
(see section 7).

## 3. Assumptions and constraints

Assumptions:
- "Alphanumeric" means ASCII `[a-z0-9]` after lowercasing, per the acceptance
  criteria's ASCII framing.
- `TypeError` on non-`str` input is acceptable (not specified).

Design decisions and trade-offs (recorded per digest rule 18):
- Single precompiled regex `[^a-z0-9]+` applied after `str.lower()`, then
  `strip("-")`: one pass, simple, and satisfies all three behavioral criteria
  simultaneously (collapse, edge-trim, empty-in/empty-out).
- Non-`str` input raises `TypeError` rather than coercing — fail-fast beats
  silently producing an identifier from e.g. `None`.
- Non-ASCII letters (e.g. `é`) are treated as separators, not transliterated.
  Trade-off: predictable ASCII-only identifiers vs. losing accented letters;
  the task specifies only ASCII lowercasing, so no transliteration dependency
  was added.
- Tests locate the module via a relative `sys.path` insert (`../src` from the
  test file), keeping the package self-contained with no install step.

Constraints: budgets of 10 wall-clock minutes, 25 tool calls, and
USD 1.00 model cost (tag `first-live`); all respected.

## 4. Acceptance criteria

- Empty and whitespace-only input returns empty string (test proves it).
- ASCII letters lowercased, runs of non-alphanumerics collapse to single
  hyphens (tests prove it).
- No leading or trailing hyphens (test proves it).
- Deliverables restructured to the repo-relative paths in `required_outputs`
  (within the workspace).
- `handoff.md` at workspace root keeps the ten canonical section titles, in
  order, with the gate-claim line corrected to `role: HUMAN` (reviewing gate),
  while the front-matter `role: SDE` (authorship) stays.

All criteria are met; evidence in section 6.

## 5. Known risks and unresolved questions

- Non-ASCII titles may collapse to short or empty identifiers (e.g. a fully
  non-Latin title returns `""`); callers needing Unicode support require a
  follow-up change.
- No uniqueness guarantee: distinct titles can map to the same identifier
  ("Hello, World" and "hello world" both → `hello-world`). Deduplication is
  out of scope.
- No length cap on output; extremely long titles yield equally long ids.
- Resolved (was open in v1.0.0): canonical section titles were unavailable in
  the workspace; the TASK-003 envelope has since supplied them and this
  document is re-headed accordingly.
- No other open defects; all tests pass.

Security, privacy, and compliance notes:
- Pure function; no I/O, network, secrets, telemetry, or dependencies beyond
  the standard library (`re`).
- No customer or production data used; test fixtures are synthetic strings.
- Data classification: internal. No DPC-relevant processing introduced.
- Regex uses a simple character-class quantifier; no catastrophic-backtracking
  pattern (linear behavior).

## 6. Evidence of self-review

Executed in sandbox (Python 3.12, pytest 9.1.1):
- `python3 -m pytest projects/PROJECT-000/tests/ -q` → `24 passed`
  (re-verified 2026-07-22, `24 passed in 0.02s`).
- `python3 -m doctest projects/PROJECT-000/src/titlecase_id.py` → 2 passed,
  0 failed (re-verified 2026-07-22).

Coverage by criterion: empty/whitespace/punctuation-only inputs (7 tests),
lowercasing and run-collapsing incl. digits and mixed punctuation (7 tests),
edge-hyphen absence (7 tests), type errors (4 tests, beyond spec).

Reviewer verification steps:
1. From the workspace root run:
   `python3 -m pytest projects/PROJECT-000/tests/ -q` (expect 24 passed).
2. Optionally: `python3 -m doctest projects/PROJECT-000/src/titlecase_id.py`
   (expect silent success).
3. Spot-check behavior: `titlecase_id("  Hello,   World!! ")` → `hello-world`;
   `titlecase_id("   ")` → `""`; `titlecase_id("---A---")` → `"a"`.
4. Confirm file paths match the task envelope's `required_outputs`.

## 7. Version identifiers

- `projects/PROJECT-000/src/titlecase_id.py` —
  artifact_id: SDE-TASK-003-src-titlecase-id, version 1.0.0, status DRAFT.
- `projects/PROJECT-000/tests/test_titlecase_id.py` —
  artifact_id: SDE-TASK-003-tests-titlecase-id, version 1.0.0, status DRAFT.
- `handoff.md` — artifact_id: SDE-TASK-003-handoff, version 1.2.0
  (v1.1.0 re-headed to canonical section titles; v1.2.0 corrects the
  gate-claim line from `role: SDE` to `role: HUMAN` per the TASK-003
  envelope — the claim names the reviewing gate, and the human owner
  reviews this delivery), status READY_FOR_REVIEW.

## 8. Recommended next action

Submit this package to the human owner for review (reviewing gate: HUMAN,
per the TASK-003 envelope), using the reviewer verification steps in
section 6. Per digest rules 2/3, the SDE authored this work and does not
approve it.

## 9. Next owner

HUMAN (human owner) reviews this delivery, per the TASK-003 envelope;
requested by PJM for business acceptance thereafter.

## 10. Out of scope

- Unicode transliteration / non-ASCII letter support.
- Identifier uniqueness or deduplication across titles.
- Output length capping or truncation.
- Packaging, publishing, or production deployment (deployment requires
  human-owner approval per digest rule 4 and is not part of this task).
