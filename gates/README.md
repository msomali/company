# gates/ — Gate Decision Records (v2 §8, §78 row 4)

Written only by the gate-writer CI (B5.2): every merged PR (except `gate/*`
heads — recursion guard) produces a `GATE-*.yaml` validated against
`control/schemas/gate.json`, landed via an auto-opened `gate/pr-<N>` PR that
the human owner merges (main requires a PR for every identity, v2 §79).

Role attribution inside a record is *claimed*, not proven (§86-C6); the owner
verifies attribution when merging the gate PR. Hand-authored files in this
directory are a policy violation — treat any as an incident.
