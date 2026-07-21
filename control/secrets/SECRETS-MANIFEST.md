# Secrets Manifest — NAMES ONLY (Bootstrap Annex BA-3). Values NEVER appear in this repo.
| Name | Purpose | Destination | Read by | Owner | Rotation |
|---|---|---|---|---|---|
| GH_TOKEN_AGENTICFOUNDRYBOT | all agent commits/PRs (ADR-B000) | GitHub Actions secret + workspace-local file (see note) | gate-writer, handoff-check, all worker agents | <HUMAN> | 90d |
| LITELLM_MASTER_KEY | proxy admin — **Mode P fallback only; do not create under Mode S (ADR-B003)** | host env /etc/company/dispatcher.env (+ /etc/company/proxy.env at reactivation — B2.1 compose reads it there) | dispatcher, proxy | <HUMAN> | 90d |
| PROXY_DB_PASSWORD | proxy virtual-key store (Postgres) — **Mode P fallback only (ADR-B003)** | /etc/company/proxy.env | proxy compose only | <HUMAN> | 90d |
| DATABASE_URL | proxy→Postgres DSN (embeds PROXY_DB_PASSWORD) — **Mode P fallback only (ADR-B003)** | /etc/company/proxy.env | proxy only | <HUMAN> | with PROXY_DB_PASSWORD |
| AGENT_VKEY_{PJM,SAA,UUD,SDE,SAT,SSE,DPC,DCE,DE,AIE,TW,ALE,LIN} | 13 per-agent proxy virtual keys (budget-scoped) — **Mode P fallback only; created by keys-bootstrap.sh at B2.2** | /etc/company/agent-keys/<CODE>.key (700 dir, 600 files) | dispatcher (injects at spawn) | <HUMAN> | 90d or key suspension |
| PROVIDER_KEY_PRIMARY | model provider — **Mode P fallback only; key exists but MUST NOT be placed under Mode S (ADR-B003)** | proxy container env_file | proxy only | <HUMAN> | 90d |
| PROVIDER_KEY_SECONDARY | fallback provider — **Mode P fallback only; key exists but MUST NOT be placed under Mode S (ADR-B003)** | proxy container env_file | proxy only | <HUMAN> | 90d |
| APPROVALS_CHANNEL_TOKEN | approvals capture | host env /etc/company/dispatcher.env | dispatcher | <HUMAN> | 90d |
| DISPATCHER_DEPLOY_KEY | dispatcher git push (ed25519 deploy key, rw; owner rider PR #17) — **never a PAT copy**; revocation = delete key on repo (kill-switch integration B4.4) | /srv/company/.ssh/dispatcher_deploy_key (600, dispatcher-owned; pubkey registered on repo) | dispatcher only | <HUMAN> at install | 180d or on incident |
| GATEWAY_AUTH_TOKEN | gateway operator/dashboard auth (v2 §85.2) **+ dispatcher spawn access** (activation item 1, 2026-07-21) | host file `/home/<user>/.openclaw/secrets/gateway-token` via SecretRef (file provider, id `value`) — outside every workspace; **generated** with `openssl rand -hex 32`, never hand-copied. **Second destination:** `/etc/company/dispatcher.env` as `OPENCLAW_GATEWAY_TOKEN` (root:dispatcher 640) — same secret by design, no separate operator token (owner ruling 2026-07-21): rotation severs dispatcher spawn access and dashboard login in one act (coupling noted in killswitch-drill SOP) | gateway at startup; human for dashboard login; dispatcher (spawn pre-flight, session_backend.py) | <HUMAN> | 90d (regenerate file + gateway restart + update dispatcher.env) |
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
