# §88 check 11 — cost report (raw evidence)

- Date: 2026-07-18 (PDT); actor: A; RUNBOOK-B7.2 row 11; Mode S (ADR-B003)

## Metering leg (PASS)

Driver `check11_meter.py` (estimation basis documented in its docstring —
artifact-derived, ~4 chars/token, reproducible; P2(b): no per-call provider
counts exist because model work rode the bootstrap session):

    prices as_of 2026-07-16 (staleness guard passed)
    metered [SDE] in=895 out=1666 running_cost=0.09225
    metered [SAT] in=2561 out=865 running_cost=0.16111
    usage.yaml: {'total_input_tokens': 3456, 'total_output_tokens': 2531,
                 'total_estimated_cost_usd': 0.16111, 'calls': 2,
                 'prices_as_of': '2026-07-16'}
    ceiling check: 0.16111 <= 5.0 OK

- Two `model_usage` events appended to log.jsonl
  (anthropic/claude-fable-5, priced via prices.yaml at record time).
- §81.3 ceiling guard exercised: 0.16111 USD ≤ envelope ceiling 5.0 USD.
- Per-agent attribution: SDE = call 1, SAT = call 2 (documented order) —
  the usage record itself has NO agent field. Friction (below).

## metrics_weekly leg — FAILED as shipped, fixed by PR

First run (pre-fix, verbatim from METRICS-2026-W29.md):

    | Episode packages in window | 0 — no episode packages (idle-by-design during bootstrap) |
    | Metered tokens (in/out) | 0 / 0 |
    | Estimated cost (USD, Mode S) | 0.0 |

Zeros despite a metered episode. Root causes:

1. `collect_tasks` scans `<root>/episodes/` only; real episodes live under
   `projects/<PROJECT>/episodes/` — the module was never pointed at the
   actual layout.
2. Latent crash: it iterates `usage.yaml` `calls` as a per-call list, but
   `metering.py` writes `calls` as an int counter with totals — the
   metrics test fixture invented a format the meter never produces
   (modules built on divergent assumptions, unintegrated until §88.11).
3. Per-agent gap: no mechanism records which agent consumed the tokens
   (§88.11 says "per-agent usage") — under ADR-B000/P2(b) attribution is
   documentation-only. Activation-era fix candidate: `agent` field in
   `record_usage` + log event.

All three recorded as B7.4 friction; 1–2 fixed in the metrics fix PR
(§78 mechanism fix per §88's friction rule); post-fix run shows the task's
tokens/cost — see the fix PR and re-run output appended below.

## Post-fix run

(appended after fix) — see commit referenced in the check-11 report.
