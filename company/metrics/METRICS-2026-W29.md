---
artifact_id: METRICS-2026-W29
title: Weekly metrics 2026-W29 (v2 §78 row 26)
type: metrics-report
project: company
owner: bootstrap agent (agenticfoundrybot)
version: "1.0"
status: APPROVED
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
---

# Weekly Metrics — 2026-W29

Window 2026-07-11 → 2026-07-17 (7 days). Sources: git history, gates/, control/escalations/, episodes/ (v2 §60–61 Phase-1 scope).

| Metric | Value |
|---|---|
| Merged PRs (main, first-parent) | 29 (#1, #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #25, #26, #27, #28, #29) |
| Revert commits | 0 |
| Gate records decided | 2 |
| Gate decisions | {'APPROVED': 2} |
| Gate owners | {'HUMAN': 2} |
| Gate-rejection rate | 0.0 |
| Escalations opened (ESC / INC) | 1 / 0 |
| Episode packages in window | 0 — no episode packages (idle-by-design during bootstrap) |
| Task success rate | no closed tasks |
| Task latency median (min) | no data |
| Metered tokens (in/out) | 0 / 0 |
| Estimated cost (USD, Mode S) | 0.0 |

```yaml
window:
  since: '2026-07-11'
  until: '2026-07-17'
  days: 7
git:
  merged_prs:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  - 8
  - 9
  - 10
  - 11
  - 12
  - 13
  - 14
  - 15
  - 16
  - 17
  - 18
  - 19
  - 20
  - 21
  - 22
  - 23
  - 24
  - 25
  - 26
  - 27
  - 28
  - 29
  merge_count: 29
  revert_count: 0
gates:
  decided: 2
  by_decision:
    APPROVED: 2
  by_owner:
    HUMAN: 2
  rejection_rate: 0.0
escalations:
  ESC: 1
  INC: 0
tasks:
  packages: 0
  note: no episode packages (idle-by-design during bootstrap)
```
