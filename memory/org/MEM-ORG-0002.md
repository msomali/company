---
memory_id: MEM-ORG-0002
namespace: org
type: observed
subject: Emergency scripts must discover live system state, not assume install-doc defaults
scope: all operational/emergency scripting (kill switch, rotation, restore paths)
source: "owner kill-switch drill report 2026-07-17 (five ranked defects); fix PR B4.4-drill-fixes"
creator: bootstrap agent (agenticfoundrybot), from owner drill findings
confidence: verified
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
expires: null
retention: keep while any emergency script exists; review at §87
supersedes: null
superseded_by: null
related: ["control/scripts/kill_switch.sh", "control/sops/killswitch-drill.md", "MEM-ORG-0001"]
---

# Emergency scripts: discover, don't assume

The first live kill-switch drill (2026-07-17) found five defects, every one
the same species: the script trusted written assumptions over live state.

1. Wrote to an evidence dir it never created (redirect failed silently).
2. Ran a user-context binary from root's PATH and fell back to a system
   unit that doesn't exist — the revocation leg silently no-opped.
3. Filtered a deploy key by its install-doc suggested title; the live key
   was registered under a different one — matched nothing.
4. Assumed root has authenticated admin `gh` — it doesn't, by design.
5. Printed a restore command with a path and title that were never live.

Rules extracted:

- Derive identifiers from the live system (`git config core.sshCommand`,
  key listings) at run time; never hard-code what an install doc suggested.
- Execution context is part of correctness: user units vs system units,
  root PATH vs user PATH, whose credentials a step actually holds.
- Create directories before redirecting into them; silent redirect failure
  in an emergency script is evidence loss (§63 audit-loss class).
- Steps needing credentials the executing context lacks must be printed
  owner commands, never best-effort executed.
- Capture verification read-backs at action time (freeze read-back at
  freeze time), not retrospectively.
- Corollary: an undrilled emergency script is a hypothesis, not a control
  (hardening row 9 exists for this reason).
