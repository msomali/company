# Branch Protection & Repo Settings Spec — B1.2 (H-EXEC)

Bootstrap prepares (this file); the human owner executes and pastes evidence
below (BA-5.4). Enforces POL-001 (policy-set-v0) and v2.4 §80 as amended by
ADR-B000. Repo visibility context: ADR-B004 (public; **never flip private
without Pro** — it silently disables everything below).

## Verified current state (bootstrap read-back, 2026-07-16)

Via `GET /repos/msomali/company/branches/main` (non-admin view):
- `protected: true` — classic branch protection enabled on `main`.
- `required_status_checks.enforcement_level: off`, contexts `[]` — expected pre-B1.3.
- Review/enforce_admins details are admin-only; owner attested (ADR-B004):
  required review = 1 + enforce_admins. Owner confirms via read-back in Phase E.
- Rulesets: none (`/rules/branches/main` = `[]`). Classic protection is the mechanism.

## Target specification for `main`

| Setting | Value | Rationale |
|---|---|---|
| Require pull request before merging | ON | BA-5.1: one task = one branch = one PR |
| Required approving review count | 1 | v1 §8 creator ≠ approver |
| Require review from Code Owners | ON | CODEOWNERS gate paths (v2.4 §80); blocks bot self-approval on /control, /company, /memory |
| Dismiss stale approvals on new commits | ON | approvals must cover what merges |
| Require conversation resolution | ON | review comments are gate content |
| Enforce for admins (`enforce_admins`) | ON | owner is also subject to gates |
| Allow force pushes | OFF | history integrity (episodes/gates reference SHAs) |
| Allow deletions | OFF | protect mainline |
| Required status checks | **Phase 2 (with B1.3):** `lint`, `handoff`, `gitleaks`; `strict: true` | contexts = Actions job ids (frontmatter-lint→`lint`, handoff-check→`handoff`, secret-scan→`gitleaks`). Enabling before B1.3 implements them would hard-block every PR — the B1.3 PR itself turns them green, so apply this phase when the B1.3 PR is open and its checks appear |
| `eval-runner`/`gate-writer` checks | NOT required | path-filtered / post-merge; requiring them would block unrelated PRs on "expected — waiting" forever |

## CODEOWNERS REQUIRED-INPUT (owner-only, BA-2.3)

Replace `<HUMAN>` with `@msomali` (4 occurrences + the trailing comment reference):

```bash
cd ~/company && git checkout -b owner/b1.2-codeowners main
sed -i 's/<HUMAN>/@msomali/g' CODEOWNERS
git add CODEOWNERS && git commit -m "B1.2: fill CODEOWNERS owner handle (REQUIRED-INPUT)"
git push -u origin owner/b1.2-codeowners
# open PR; bootstrap reviews per interim owner-PR rule; you merge
```

Note: "Require review from Code Owners" only bites once this is merged.

## Phase 1 — apply now (owner, admin credentials)

UI path: Settings → Branches → edit rule for `main`, per the table above.
Or exactly, via API (run as msomali, NOT the bot — bot has no admin):

```bash
gh api -X PUT repos/msomali/company/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
```

## Phase 2 — apply when the B1.3 PR is open and its three checks have run

```bash
gh api -X PATCH repos/msomali/company/branches/main/protection/required_status_checks \
  -F strict=true -f "contexts[]=lint" -f "contexts[]=handoff" -f "contexts[]=gitleaks"
```

## Phase E — evidence read-back (owner; paste output below)

```bash
gh api repos/msomali/company/branches/main/protection \
  --jq '{enforce_admins:.enforce_admins.enabled,
         reviews:.required_pull_request_reviews | {count:.required_approving_review_count, code_owners:.require_code_owner_reviews, dismiss_stale:.dismiss_stale_reviews},
         checks:.required_status_checks,
         force_pushes:.allow_force_pushes.enabled, deletions:.allow_deletions.enabled,
         conversation:.required_conversation_resolution.enabled}'
```

### Evidence — Phase 1 (owner paste + date)

{
  "checks": null,
  "conversation": true,
  "deletions": false,
  "enforce_admins": true,
  "force_pushes": false,
  "reviews": {
    "code_owners": true,
    "count": 1,
    "dismiss_stale": true
  }
}

Attested by: msomali, 2026-07-16

### Evidence — Phase 2 (owner paste + date, at B1.3)

{
  "checks": {
    "checks": [
      {
        "app_id": 15368,
        "context": "lint"
      },
      {
        "app_id": 15368,
        "context": "handoff"
      },
      {
        "app_id": 15368,
        "context": "gitleaks"
      }
    ],
    "contexts": [
      "lint",
      "handoff",
      "gitleaks"
    ],
    "contexts_url": "https://api.github.com/repos/msomali/company/branches/main/protection/required_status_checks/contexts",
    "strict": true,
    "url": "https://api.github.com/repos/msomali/company/branches/main/protection/required_status_checks"
  }
}

Attested by: msomali, 2026-07-16 — Phase 1 and Phase 2 both applied and read back; B1.2 complete.

Note: applied via full PUT — the spec's PATCH returns 404 while checks are null from Phase 1.
