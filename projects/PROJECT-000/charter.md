---
artifact_id: projects/PROJECT-000/charter.md
title: PROJECT-000 Dry-Run Charter
type: charter
project: PROJECT-000
owner: PJM
version: "1.0"
status: READY_FOR_REVIEW
sensitivity: internal
created: REQUIRED-INPUT
updated: REQUIRED-INPUT
approval: null   # human signs at B7.1
---
# PROJECT-000 — Synthetic Dry-Run Project (v1.1 §56; v2.1 §88)
```yaml
project_id: PROJECT-000
product: A slugify utility library used solely to exercise every Phase 1 mechanism.
target_customer: internal (the company itself)
problem_evidence: v2.1 §88 requires a synthetic project; no external claim made.
success_metric: {metric: "§88 checks passed", baseline: 0, target: 14, horizon: REQUIRED-INPUT}
scope: [checks 1-14 of v2.1 §88]
non_goals: [production deployment, external users, real customer data]
default_tier: T2
budget_ceiling: {money_per_month: REQUIRED-INPUT, model_budget_tag: dryrun}
timebox: REQUIRED-INPUT
kill_criteria:
  - any §88 check unpassable after two remediation attempts -> ESC to human
  - dry-run model spend exceeds budget_ceiling
  - two weeks elapsed without completing B7.2
decision_date: REQUIRED-INPUT
approval: REQUIRED-INPUT
```
