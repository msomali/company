# §88 check 14 — failing golden task blocked by eval CI, fixed, merged, tagged (raw evidence)

- Date: 2026-07-19 (PDT); RUNBOOK-B7.2 row 14; §88.14 verbatim.
- Vehicle: **PR #73** (base `main`, head `bootstrap/check14-eval-case`) — an
  eval-bundle PR adding golden task `SDE-GT-003` (post-SAT slugify contract
  incl. the SAT-53-F1 non-decomposable-script pinning, TASK-001):
  `control/evals/sde/case-003.yaml` + `fixture-003/`. The case is
  `expect: pass` — a genuinely failing golden task on the red leg, distinct
  from the GT-002 seeded-harness case.
- Gate 0 P3 window (owner acts; **bot cannot read branch protection** — the
  protection API returns 404 to the workspace PAT, no admin scope): `evals`
  temporarily added to the required contexts **for the check-14 window only**,
  bracketed by before/after read-backs, reverted immediately after.
  Required contexts during the window: **{lint, evals, handoff, gitleaks}**.

## Red leg — failing golden task blocks the PR (commit `6f1be64`)

- Deliberate defect (`fixture-003/src/slugify.py`): the leading/trailing
  separator trim is removed — `return _NON_ALNUM.sub("-", ascii_text)` with
  `# DEFECT: missing .strip("-")`. The golden task therefore fails its tests
  and eval CI must block the PR.
- Verbatim CI conclusions on `6f1be64` (GitHub check-runs API):
  - `evals`    → **failure**   ← §88.14 primary gate (eval CI red)
  - `lint`     → **failure**   ← failing step: "unit tests (all control/scripts)"
  - `gitleaks` → success
  - `handoff`  → success
  → **2 of 4 required status checks failing.**

### Block form (check-14 specific — NOT a scripted merge attempt)

The merge was refused by **GitHub's own required-check enforcement**: with two
required contexts red, the PR merge display showed *"2 of 4 required status
checks failing"* (owner-attested) and the merge control was disabled. **No
scripted `PUT /merge` was issued** for check 14. This form is deliberately
distinct from checks 6 and 9, which DID script `PUT /merge` — because those
checks tested separation-of-duties (6) and release-authority (9) respectively,
and each captured a verbatim HTTP **405**. Check 14's §88.14 property —
"blocked by eval CI" — is a property of the **required-check state**, so it is
demonstrated by that state (evals in required contexts + red run `6f1be64`),
not by an API refusal body. No HTTP 405 body is invented or claimed here.

### Parallel corroboration — the path-filter hazard (item 16)

Gate PR **#74** (`gate/pr-73`, head `ca1bf5d`) touches only
`gates/GATE-HUMAN-PR73-f4325282.yaml`, which does **not** match the eval-runner
path filter — so the `evals` workflow never triggers on it. Its check-runs are
`{gate, handoff, gitleaks, lint}` — **no `evals`** (bot-verified via check-runs
API). With `evals` required during the window, that never-reported context left
#74 (and the other gate PRs) hanging on *"Expected — Waiting for status to be
reported."* They unhung only when the owner reverted the toggle. This is the
required-check-state block seen from the other side: a required check that
cannot report is as un-mergeable as one that reports red.

## Green leg — fix turns it green (commit `5c42c69`)

- Fix: restore the trim — `return _NON_ALNUM.sub("-", ascii_text).strip("-")`.
- Verbatim CI conclusions on `5c42c69` (check-runs API): `lint` success,
  `evals` success, `handoff` success, `gitleaks` success, `gate` success —
  all green. With every required context green, the PR became mergeable.

## Merge + release tag (owner acts)

- PR #73 merged to `main` by **@msomali** — **merge SHA
  `f43252825995351599447a8b33c890297e6e0855`** (`f432528`). Parents:
  `3b2569c` (prior `main`) and **`5c42c69`** (the green leg) as the second
  parent — the fixed, all-green tree is what landed (bot-verified:
  `merge-base --is-ancestor 5c42c69 f432528` → true).
- Annotated tag **`evals-v1.0`** → tag object `0cca19f` → dereferences to
  commit **`f432528`** (the merge commit); tagger @msomali; message:
  *"First eval-gated bundle (§88.14): golden task red→fixed→merged"*. The tag
  sits on the merge commit, as required.
- Toggle reverted after the merge (owner-attested after-read-back): required
  contexts back to **exactly {lint, handoff, gitleaks}** — `evals` removed.
  Evals-required was a dry-run-window state, not the steady config; steady-state
  evals-required is the post-bootstrap branch-protection review's call
  (RUNBOOK-B7.2 Gate 0 P3).

## Item 16 — the lint↔evals coupling is INTENTIONAL (do not remove)

The eval suite is exercised on every PR by **two** required checks, by design:

- **`evals`** (workflow `eval-runner.yml`) runs `eval_runner.py` directly, but
  is **path-filtered** (`paths: control/prompts/**`, `control/manifests/**`,
  `control/policies/**`, `control/evals/**`, `control/scripts/eval_runner.py`).
  The filter is the **intentional P3 mitigation**: it stops a required eval
  check from hanging PRs that don't touch eval-relevant paths (the path-filter
  hazard — exactly what stranded gate PR #74 above during the window).
- **`lint`** (workflow `frontmatter-lint.yml`, **no** path filter, runs on
  every PR) executes `pytest control/scripts/tests`, which includes
  `test_eval_runner.py::test_full_suite_behaves_as_expected` — the same runner
  over the same `case_glob: control/evals/*/case-*.yaml`. So a broken golden
  task also reddens `lint`, on **every** PR. (This is why `lint` went red on
  the red leg, at the "unit tests (all control/scripts)" step.)

This redundancy is the **counterpart** to the path filter: the filter keeps
`evals` from hanging unrelated PRs; the lint-side full-suite guard keeps eval
regressions caught on **every** PR, closing the coverage gap the filter opens.
**Removing either side regresses the other** — do NOT "de-duplicate" the
lint-side eval-suite guard, and do NOT loosen/remove the `evals` path filter to
compensate. Recorded as B7.4 doc item 16; **owner ruling 2026-07-19: the
coupling is intentional and must not be removed.**

## Result

- Red leg: **PASS** — failing golden task `SDE-GT-003` blocked PR #73 via
  required-check enforcement (2 of 4 required failing; `evals` the §88.14 gate;
  `lint` redundantly red via the intentional coupling).
- Green leg: **PASS** — trim restored, all required contexts green.
- Merge + tag: **PASS** — merged `f432528`; annotated `evals-v1.0` on the merge
  commit.
- **Check 14 overall: PASS.** Block form for the record: required-check-state
  refusal (not a scripted merge attempt) — distinct from checks 6/9.
