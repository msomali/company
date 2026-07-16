# Secrets Manifest — NAMES ONLY (Bootstrap Annex BA-3). Values NEVER appear in this repo.
| Name | Purpose | Destination | Read by | Owner | Rotation |
|---|---|---|---|---|---|
| GH_TOKEN_AGENTICFOUNDRYBOT | all agent commits/PRs (ADR-B000) | GitHub Actions secret + workspace-local file (see note) | gate-writer, handoff-check, all worker agents | <HUMAN> | 90d |
| LITELLM_MASTER_KEY | proxy admin — **Mode P fallback only; do not create under Mode S (ADR-B003)** | host env /etc/company/dispatcher.env | dispatcher, proxy | <HUMAN> | 90d |
| PROVIDER_KEY_PRIMARY | model provider — **Mode P fallback only; key exists but MUST NOT be placed under Mode S (ADR-B003)** | proxy container env_file | proxy only | <HUMAN> | 90d |
| PROVIDER_KEY_SECONDARY | fallback provider — **Mode P fallback only; key exists but MUST NOT be placed under Mode S (ADR-B003)** | proxy container env_file | proxy only | <HUMAN> | 90d |
| APPROVALS_CHANNEL_TOKEN | approvals capture | host env /etc/company/dispatcher.env | dispatcher | <HUMAN> | 90d |
| GATEWAY_AUTH_TOKEN | gateway operator/dashboard auth (v2 §85.2) | host file `/home/<user>/.openclaw/secrets/gateway-token` via SecretRef (file provider, id `value`) — outside every workspace; **generated** with `openssl rand -hex 32`, never hand-copied | gateway at startup; human for dashboard login | <HUMAN> | 90d (regenerate file + gateway restart) |
Verification: existence-only checks (exit codes). Printing any value, even masked, is prohibited.

**Sandbox mount rule (learned in Phase 0):** OpenClaw blocks bind-mounting any
system path (/etc/*, credential stores, docker.sock) into a sandbox container.
The bot token file MUST live inside the agent's own workspace tree, e.g.
`~/company/.secrets/gh-token` (absolute path, no `~`, in the docker `binds` config —
JSON does not expand tildes). Add `.secrets/` to `.gitignore` before the token file
is ever created, and confirm the file mode is 600.
Governance: this placement is ADR-B002; the accepted risk is registered as v2 §86-C7.
Mode S (ACTIVE, ADR-B003) note: model-auth credentials are NOT secrets in this manifest — the Anthropic setup-token (long-lived, minted via Claude Code) and the OpenAI OAuth profile (auto-refresh) live only in OpenClaw per-agent auth stores (`~/.openclaw/agents/<id>/agent/`), created by human sign-in, never in the repo, never in any workspace.

**Audit baseline under Mode S (field-validated 2026-07-15):** `openclaw secrets audit --check` reports the auth-store setup-token as a plaintext finding and the OAuth profile as legacy residue — both **by design**. Record the exact counts in hardening evidence row 6 and diff future audits against that baseline; do not chase zero findings into the auth store, and never hand-edit the agent sqlite.
