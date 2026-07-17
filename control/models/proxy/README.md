# Mode P proxy — LiteLLM (DORMANT fallback; do not start)

**Status: DORMANT (ADR-B003).** Mode S is ACTIVE. Nothing in this directory
runs, and no secret named here may be created or placed, until an
**owner-approved Mode P reactivation ADR** exists. Authored warm at B2.1 per
v2 §81 Mode P; first start + smoke test is B2.2 (H-EXEC, conditional).

## Contents

| File | Purpose |
|---|---|
| `docker-compose.yaml` | LiteLLM + Postgres, loopback-only, compose profile `mode-p` (a bare `docker compose up` starts nothing) |
| `litellm-config.yaml` | Routes the three §81 policies to provider models per `../policies.yaml`; fallbacks mirror MODEL-001/002 |
| `keys-bootstrap.sh` | Creates the 13 per-agent virtual keys with policy scoping + budget tags (run once at reactivation) |
| `smoke-test.sh` | B2.2 acceptance: one call per policy through the proxy |

## Custody rules (v2 §80.4, §81; SECRETS-MANIFEST)

- Secret **names only** in this repo. Values live in `/etc/company/proxy.env`
  (root:root, 600) on the host — created only at reactivation.
- `PROVIDER_KEY_PRIMARY` = Anthropic, `PROVIDER_KEY_SECONDARY` = OpenAI.
  Keys exist provider-side but are **not placed anywhere** under Mode S.
- `LITELLM_MASTER_KEY` is dispatcher/proxy-only; never in any agent context.
- Budget alert thresholds come from `../policies.yaml` `mode_p.budget_alert_thresholds`
  (0.60 / 0.85); hard monthly caps and alert webhook are REQUIRED-INPUT at
  reactivation (`AGENT_MONTHLY_BUDGET_USD`, `ALERT_WEBHOOK_URL`).
- Breaker = key suspension (`/key/block`); kill switch integration at B4.4.

## Reactivation checklist (condensed from ADR-B003)

1. Owner approves a reactivation ADR (records why Mode S is insufficient).
2. Owner creates `/etc/company/proxy.env` from the variable names in
   `docker-compose.yaml` — values never enter the repo.
3. `docker compose --profile mode-p up -d` (B2.2, H-EXEC).
4. `keys-bootstrap.sh` (creates per-agent keys), then `smoke-test.sh`
   (one call per policy); commit evidence.
5. Update `../policies.yaml` `mode: P` via PR (eval CI applies, v2 §81).

Config is authored against the LiteLLM v1 documented schema; runtime behavior
is deliberately unverified while dormant — verification IS the B2.2 smoke test.
