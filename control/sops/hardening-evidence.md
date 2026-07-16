# Hardening Evidence — v2.1 §85 (task B0.1). Human completes; commit precedes ANY activation.
| # | Item | Evidence (command output ref / screenshot path / config commit) | Date | Done |
|---|------|---|---|---|
| 1 | Version floor incl. fixes for CVE-2026-25253 and CVE-2026-32922; weekly advisory SOP active | OpenClaw 2026.7.1 (2d2ddc4) via npm, latest stable at provisioning (subsumes both named CVE fixes); Claude Code CLI installed as documented dependency (BA-4 rev 1.2); weekly advisory review per SOP in force | 2026-07-15 | [x] |
| 2 | Gateway auth enabled; no default/empty/shared tokens | gateway.auth.token migrated to file SecretRef (provider `default`, id `value`) at /home/mr-robot/.openclaw/secrets/gateway-token, dir 700 / file 600; value generated via `openssl rand -hex 32` (rotated 2026-07-15 after placeholder incident + chat exposure — old value never valid); `secrets audit --check` clean of config plaintext; rotation procedure = regenerate file + `openclaw gateway restart`; dashboard auto-auth disabled for SecretRef tokens (by design, one paste per browser) | 2026-07-15 | [x] |
| 3 | Loopback bind; Tailscale/SSH-tunnel only; external exposure check performed | `gateway status`: bind=loopback, listening 127.0.0.1:18789 + [::1]:18789 only; VM behind VMware NAT, no LAN peer available for external probe — exposure check N/A at this topology; MUST re-verify if bind or VM networking ever changes | 2026-07-15 | [x] |
| 4 | Per-agent containers; scoped mounts; egress allowlist; read-only roots where practical | bootstrap: image company/bootstrap:1 (ubuntu:24.04 + git, python3, pytest, pyyaml, jsonschema, gh, unzip); sandbox mode=all scope=agent workspaceAccess=rw; tool policy (agent): allow read/write/edit/apply_patch/exec/process, deny image/sessions_*/subagents/session_status/browser/canvas/nodes/cron/gateway (per `sandbox explain` 2026-07-15); **egress: bridge (FULL) — allowlist via DOCKER-USER iptables PENDING, hard-required before §87 activation**; per-agent images arrive at B3.x | 2026-07-15 | [ ] in progress (by design: allowlist + B3.x) |
| 5 | Skills vendored-only; review checklist in force; hashes pinned | Zero installed marketplace/ClawHub skills — standing rule, never install; doctor "Eligible: 17" = bundled platform skills (not installs); 30 missing-requirement skills disabled via `doctor --fix` 2026-07-15; no skills allowlist mechanism configured in 2026.7.1 ("Blocked by allowlist: 0" = none defined) | 2026-07-15 | [x] |
| 6 | Per-agent scoped credentials; no broad OAuth/browser-profile grants; prod creds only in DCE path | Mode S (ADR-B003): anthropic `anthropic:default` setup-token (long-lived, minted via Claude Code, re-minted 2026-07-15 after invalid-token incident; password-manager copy + rotation reminder); openai OAuth profile (auto-refresh); both in per-agent auth stores, host-side, outside all workspaces; accepted `secrets audit --check` baseline = plaintext=1 (setup-token, by design) + legacy=1 (OAuth residue, by design) — do not chase zero; command owner UNSET (correct at zero channels; mandatory at first channel); provider API keys exist but UNPLACED per ADR-B003; bot PAT = classic, repo+workflow scopes, 90d expiry (fine-grained structurally impossible for collaborator repos — GitHub limitation), stored in workspace file (600, gitignored, ADR-B002/§86-C7) + Actions secret GH_TOKEN_AGENTICFOUNDRYBOT, fine-grained token revoked; bot account hygiene rule: collaborator on msomali/company ONLY; agent refused to print token value under probe (BA-2 observed in behavior) | 2026-07-15 | [x] |
| 7 | Browser/host-exec plugins disabled by default | tools.elevated.enabled=false (explain: failing gates enabled + allowFrom); browser tool denied for bootstrap at agent policy; codex plugin auto-installed by `doctor --fix` (first-party @openclaw/codex, required plumbing for OpenAI Codex OAuth models) — recorded as deliberate addition | 2026-07-15 | [x] |
| 8 | Dedicated VM/user; default-deny inbound firewall; patched OS; off-host repo backups | Fresh dedicated Ubuntu 24.04 arm64 VM (VMware) with layered snapshots (base-os, pre-company); apt full-upgrade at build 2026-07-15; off-host backup = GitHub remote msomali/company (live since Step 5); **firewall: run the row-8 block below, paste `ufw status verbose` here, then mark done** | 2026-07-15 | [ ] pending ufw |
| 9 | Kill switch installed and drilled | Built at B4.4; drill required before any §87 activation — pending by design | — | [ ] pending B4.4 |

Row 8 completion (run once, paste output above, flip row 8 to [x]):
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip
```bash
sudo ufw allow OpenSSH        # only if you ever ssh into this VM; skip otherwise
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

Row guidance (field-validated 2026-07-15, OpenClaw 2026.7.1 — see PHASE-0-RUNBOOK v4.1 Step 4):
- Row 1: `openclaw --version` output; latest stable at provisioning is the floor. Record `claude --version` too (setup-token mint, BA-4).
- Row 2: gateway auth ON + token held as a **file SecretRef** (never plaintext in openclaw.json); rotation = regenerate the file (`openssl rand -hex 32`) + `openclaw gateway restart`. Dashboard auto-auth is disabled for SecretRef tokens by design.
- Row 5: doctor's "Eligible: N" counts *bundled platform* skills, not installs — the evidence claim is zero **installed** skills.
- Row 6: Mode S custody = Anthropic setup-token (long-lived) + OpenAI OAuth (auto-refresh) in per-agent auth stores; record the accepted audit baseline. Command owner: unset is correct at zero channels. Provider API keys exist but are never placed (ADR-B003).

Attested by: msomali (human owner) — completes B0.1 on commit; rows 4 and 9 remain open by the annex's own progressive design and close before §87.
