---
memory_id: MEM-ORG-0005
namespace: org
type: observed
subject: "Branch divergence orphans reviewed work: never stack PRs; verify the merged SHA covers your latest push"
scope: every PR by owner or agent, permanently
source: "PR #65 orphan (breaker fix absent from main until #67, found 2026-07-18 17:38); PR #51 merge race (P3 decision commit 8568cf0 orphaned ~8h, found in the 17:58 blast-radius audit); prior L-001/MEM-ORG-0001 divergence lesson"
creator: bootstrap agent (agenticfoundrybot), from owner ruling 2026-07-18 17:58 PDT
confidence: verified
sensitivity: internal
created: "2026-07-18"
updated: "2026-07-18"
expires: null
retention: permanent while the single-repo PR workflow stands
supersedes: null
superseded_by: null
related: ["memory/org/MEM-ORG-0001.md", "projects/PROJECT-000/dryrun/RUNBOOK-B7.2.md", "control/sops/branch-protection.md"]
---

# Branch divergence orphans reviewed work — two rules, both mandatory

## Rule 1 (owner ruling): no stacked PRs

**Owner and agent PRs branch from current `main`, never from another open
PR's branch.** A stacked PR whose base merges independently orphans the
stacked work: GitHub merges the stacked PR into the abandoned base branch,
everyone sees "MERGED", and the content never reaches main.

Observed: PR #65 (the §88.12 breaker — a safety fix) was based on PR #63's
branch. #63 merged to main from an earlier branch state; #65 then "merged"
into the dead base. `record_action` was absent from main while every party
believed it deployed. Found only at check-13 setup; delivered by PR #67.

## Rule 2 (corollary from the same audit): a merge is delivery only of the
## SHA it merged

**After any merge, verify the merged head SHA covers your latest push
before treating the content as landed.** Pushing to a PR branch while the
owner merges races the merge; the commit that loses the race is silently
orphaned on the branch with no error anywhere.

Observed: PR #51's P3 decision commit (8568cf0, 09:40:51) lost the race to
the merge of head 8459b25. "P1/P2/P3 all recorded on main" was believed by
both parties for ~8 hours; the check-14 governing decision was never on
main. Restored by cherry-pick alongside this record.

## Operational form

- Need a change while your prior PR is open? Either wait for its merge and
  branch from updated main, or put the dependent commit on the SAME open
  PR — never a second PR based on the first.
- After merge: `git merge-base --is-ancestor <your-latest-sha> origin/main`
  — if false, the work did not land; say so immediately.
- Blast-radius check when divergence is found anywhere:
  `git branch -r --no-merged origin/main` + content diff each survivor.

## Enforcement candidate (not yet built)

CI check on PR open: fail when the base ref is not `main`/`release` (gate
branches exempt). Recorded as a B7.4 candidate, owner disposition.
