# Manifest → Agent-file Generator Contract (task B3.1; v1.1 §48.1)

Input: every `*.yaml` here validating against v2 §5 fields above.
Output per agent, under `control/manifests/_generated/<agent_id>/`:

- `IDENTITY.md` — role contract Identity section.
- `SOUL.md` — Mission + Thinking Framework + role principles.
- `AGENTS.md` — MUST embed, in order: (1) `company/digest-v1.1.md` fence VERBATIM
  with `{ROLE_ID}/{ROLE_NAME}` substituted; (2) Universal Working Method (v1 §10);
  (3) role Responsibilities, Collaboration, Escalation.
- `TOOLS.md` — rendered from allowed/denied tools; deny-by-default; deny wins.

Rules: generated files carry a `# GENERATED — do not hand-edit` header; the
generator is deterministic (same input → byte-identical output; CI verifies);
generation NEVER registers or activates an agent in OpenClaw (BA-2.4) —
installation into the gateway is a separate human-approved step after §88.
