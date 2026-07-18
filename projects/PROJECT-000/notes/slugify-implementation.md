---
artifact_id: projects/PROJECT-000/notes/slugify-implementation.md
title: TASK-001 slugify implementation note
type: note
project: PROJECT-000
owner: SDE (via bootstrap session, §86-C6 attribution)
version: "1.0"
status: READY_FOR_REVIEW
sensitivity: internal
created: "2026-07-18"
---

# TASK-001 — slugify(title) implementation note

SDE deliverable for TASK-001 (PROJECT-000 dry run). Model work attributed to
the SDE role through the bootstrap session per the operative §86-C6 clause
and Gate 0 P2 decision (recorded-prompt backend).

## Approach

- `unicodedata.normalize("NFKD", title)` decomposes accented characters and
  compatibility forms (ligatures ﬁ → fi); the ascii encode/ignore round-trip
  drops combining marks — unicode folding criterion.
- One compiled regex collapses every non-alphanumeric run to a single
  hyphen; `.strip("-")` trims leading/trailing separators — trimming
  criterion.
- No locale, clock, or environment dependence: output is a pure function of
  the input string — determinism criterion.

## Tests (projects/PROJECT-000/tests/test_slugify.py)

- 6 unicode-folding cases, 6 separator cases, empty/symbol-only, TypeError.
- Property tests on a fixed-seed (seed=88) 500-string corpus: output shape
  `^$|^[a-z0-9]+(-[a-z0-9]+)*$`, idempotence, determinism — 516 passing.

## Known limits

Non-Latin scripts without NFKD ascii decompositions (e.g. CJK, Cyrillic)
fold to empty runs and drop out of the slug; acceptable for charter scope
(synthetic dry run), flagged for any real adoption.
