---
memory_id: MEM-ORG-0003
namespace: org
type: observed
subject: Credential revocation authority is per-account; the owner's instant lever is access removal
scope: incident response for any machine-account credential (C7 and successors)
source: "owner C7 analysis 2026-07-17 (post-#43 backlog note); GitHub PAT + collaborator API semantics verified live (204/404 read-backs)"
creator: bootstrap agent (agenticfoundrybot), from owner analysis
confidence: verified
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
expires: null
retention: keep while any machine account holds a credential; review at §87
supersedes: null
superseded_by: null
related: ["control/sops/incident.md", "control/scripts/kill_switch.sh", "MEM-ORG-0002"]
---

# Revocation authority is per-account; access removal is the owner's lever

Against an exfiltrated machine-account token, host containment (stop
containers, stop gateway) does nothing — the token works off-host. And the
owner cannot revoke it: a PAT belongs to its account and is revocable only
from that account's own session.

The owner-side lever that works instantly and independently of token state
is **access removal** — deleting the machine account's collaborator grant.
The token stays technically alive but opens nothing.

Generalized rules:

- For every credential, record separately: who can revoke the credential
  itself, and who can sever the access it grants. They are often different
  people; the second is usually faster.
- Containment plans must state which levers work off-host; host-side stops
  only bound on-host misuse.
- Access removal has side effects on control machinery (here: dual-control
  CODEOWNERS unsatisfiable while removed) — record them next to the lever,
  not as a surprise.
