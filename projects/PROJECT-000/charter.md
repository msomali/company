---
artifact_id: projects/PROJECT-000/charter.md
title: PROJECT-000 Dry-Run Charter
type: charter
project: PROJECT-000
owner: PJM
version: "1.0"
status: APPROVED
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-18"
approval: "msomali 2026-07-18"
---
# PROJECT-000 — Synthetic Dry-Run Project (v1.1 §56; v2.1 §88)
```yaml
project_id: PROJECT-000
product: A slugify utility library used solely to exercise every Phase 1 mechanism.
target_customer: internal (the company itself)
problem_evidence: v2.1 §88 requires a synthetic project; no external claim made.
success_metric: {metric: "§88 checks passed", baseline: 0, target: 14, horizon: 2026-07-31}
scope: [checks 1-14 of v2.1 §88]
non_goals: [production deployment, external users, real customer data]
default_tier: T2
budget_ceiling: {money_per_month: "USD 50 (estimated Mode S metering vs prices.yaml; anomaly breaker, not a spend commitment)", model_budget_tag: dryrun}
timebox: 2026-07-31   # aligned with the two-week B7.2 kill criterion
kill_criteria:
  - any §88 check unpassable after two remediation attempts -> ESC to human
  - dry-run model spend exceeds budget_ceiling
  - two weeks elapsed without completing B7.2
decision_date: 2026-07-24   # mid-timebox re-review
approval: "msomali 2026-07-18 — B7.1 signed"
```
