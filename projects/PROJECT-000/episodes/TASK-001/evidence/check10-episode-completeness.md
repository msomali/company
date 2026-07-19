# §88 check 10 — episode assembly + §9 completeness (raw evidence)

- Date: 2026-07-18 (PDT); actor: A; RUNBOOK-B7.2 row 10
- Commands (both exit 0, output verbatim):

      $ episode_collector.py projects/PROJECT-000/episodes/TASK-001
      episode TASK-001: 21 file(s), complete, refs: PRs [53, 58, 61]
      $ episode_collector.py projects/PROJECT-000/episodes/TASK-001 --check
      episode TASK-001: 21 file(s), complete, refs: PRs [53, 58, 61]

## manifest.yaml §9 checklist

| Check | Result |
|---|---|
| task_envelope | true |
| state_transitions | true (14-entry history, NONE→…→DEPLOYMENT) |
| action_trace | true (log.jsonl: transitions, dispatch-era events, gate decisions) |
| cost_tokens | true (model_calls=0 in log — P2(b): model work ran through the bootstrap session, no dispatcher-metered calls; usage.yaml is check 11) |
| transcripts | true (vacuous under model_calls=0, honestly scored by the collector) |
| final_status_recorded | true (state: DEPLOYMENT) |
| **complete** | **true** |

- gate_records: all six interim-channel records harvested
  (SAT/SSE/DPC/DCE/PJM/HUMAN ×1)
- references: PRs 53, 58, 61; files: 21 (sha256 each)
- `--check` verifies manifest-vs-tree consistency: no new/changed/vanished
  files since collection.

## Caveat (honest scope)

This assembly is the check-10 mechanism demonstration. Checks 11 and 13
will mutate this episode (usage.yaml; pause/resume state history), so the
manifest MUST be re-collected as the episode's final act before the
package merges to main — otherwise `--check` goes red by design.

- Result: **PASS** — episode assembled, §9 checklist green, consistency
  check green.
