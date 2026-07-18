<!-- Handoff Package — v1 §15. CI (handoff-check) blocks merge while any item is empty.

§86-C6 gate-role claim (MANDATORY for bot-role PRs — MEM-ORG-0004):
if the head branch carries a role prefix (sde/, sat/, sse/, dpc/, dce/,
pjm/, saa/, uud/, de/, aie/, tw/, ale/, lin/), the body MUST include one
plain-text line, outside any comment, beginning with the word "role",
a colon, and the gate-owner role — e.g. the SAT claim line is the word
role, then ": SAT" — naming one of SAT / SSE / DPC / DCE / PJM (or HUMAN
to consciously claim no bot-role gate). WHY mandatory, not optional:
under ADR-B000 the author-bot cannot review its own PR, so the
approving-review-body claim channel is structurally dead for every
bot-role PR — the PR body is the only claim channel gate-writer can
parse when it emits the gate record on merge. handoff-check FAILS
role-prefixed PRs without this line. The human owner verifies the
claimed attribution at merge (§86-C6 backstop). -->
## 1. Requested deliverable
## 2. Source requirements and traceability
## 3. Assumptions and constraints
## 4. Acceptance criteria
## 5. Known risks and unresolved questions
## 6. Evidence of self-review
## 7. Version identifiers
## 8. Recommended next action
## 9. Next owner
## 10. Out of scope
