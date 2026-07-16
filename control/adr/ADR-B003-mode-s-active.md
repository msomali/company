---
artifact_id: control/adr/ADR-B003-mode-s-active.md
title: ADR-B003 — Mode S (Subscription Auth) Active; Mode P Is an Approval-Gated Fallback
type: adr
project: control
owner: human-owner
version: "1.0"
status: APPROVED
sensitivity: internal
created: <fill on merge>
updated: <fill on merge>
approval: human-owner
---

# ADR-B003 — Mode S Active

**Context.** §81 is dual-mode by design and has flipped once already: v2.3 declared
Mode S active (subscription era), v2.4 declared Mode P active (owner adopted API
keys). The owner now reverses again: provider **subscriptions** fund the agents;
API keys exist only as a fallback. The owner's explicit condition: **reactivating
Mode P requires the owner's approval** — a recorded ADR, never a silent config edit.

**Decision.**
1. `control/models/policies.yaml` declares `mode: S`.
2. Provider access = human-performed OAuth sign-ins into OpenClaw auth profiles
   (Anthropic subscription; OpenAI/ChatGPT-Codex subscription for MODEL-001).
   Token custody stays host-side in per-agent auth stores
   (`~/.openclaw/agents/<id>/agent/auth-profiles.json`) — never in the repo,
   prompts, or any workspace.
3. **No provider API keys are placed** under Mode S — the owner's pre-existing
   keys remain in the password manager / provider console only (possession is not
   placement). B2.1 (LiteLLM compose/config, names only) is still authored — a
   warm fallback. B2.2 (starting the proxy) is conditional and executes only under
   a future Mode P reactivation ADR approved by the owner.
4. Budget mechanism of record = dispatcher token metering against `prices.yaml`
   plus the plan ceiling and the global concurrency cap (§81 Mode S items 2–4).
   `prices.yaml` is therefore a mandatory B0.3 input.

**Provider-policy ground truth (as of 2026-07-14).** Anthropic's stance on
third-party harnesses moved four times in five months: early restrictions (Feb),
hard block (Apr 4), a metered Agent SDK credit plan (announced May 13, effective
Jun 15), then a **pause of that plan (Jun 15)** — subscription limits unchanged,
revision pending, advance notice promised. OpenClaw's documentation treats the
usage as provider-sanctioned "unless Anthropic publishes a new policy," and
recommends API keys as the safer production path — which is exactly the risk this
ADR accepts and the dormant Mode P hedges. OpenAI explicitly supports ChatGPT/Codex
OAuth in third-party tools including OpenClaw. Registered risk: **§86-C5 is ACTIVE**
(shared identity, shared pool and rate limits, policy volatility).

**What is accepted.** (a) Hard per-agent dollar caps are lost; enforcement is
dispatcher-metered estimates + plan ceiling — one runaway agent can starve the
shared pool (C5 backstop: breaker halts dispatch). (b) The company's model access
rides terms that changed four times this year; a fifth change may force the Mode P
flip on short notice — which is why the fallback stays warm and pre-specified.
(c) If the Agent SDK credit split returns, the per-user monthly credit + opt-in
overflow cap becomes the hard budget; credits are per-account and non-poolable.

**D5 — RESOLVED 2026-07-14: option (a).** The owner holds active subscriptions on
both providers (Anthropic + ChatGPT) and pre-existing API keys for both. Both OAuth
sign-ins are performed at B0.3 (runbook Steps 2/2b); MODEL-001 decorrelation is
satisfied under Mode S. The pre-existing keys change nothing here: they remain in
the owner's password manager / provider console and MUST NOT be placed in any repo,
workspace, OpenClaw config, or proxy env while Mode S is declared. Options (b) and
(c) are void.

**Rejected alternatives.** Staying Mode P (owner overruled — subscription economics
and no desire to pre-fund keys); a permanent hybrid (splits custody models and
doubles the §85.6 evidence surface for no Phase-1 gain).

**Affected files.** `policies.yaml` (mode: S), `prices.yaml` (active-required),
`SECRETS-MANIFEST.md` (proxy/provider-key rows marked Mode-P-fallback-only),
`BOOTSTRAP-PLAN.md` (B0.3, B2.1, B2.2), Bootstrap Annex rev 1.1 (B0.3, B2.x, BA-3
item 5, BA-4), v2.6 (§73, §78 row 28, §81, §86-C5, §88.13), Roadmap Index (D1
resolved to Mode S; D5 opened), PHASE-0-RUNBOOK v4 (Steps 0, 2, 3, 4.6, 7c, 9).

**Reactivation path (the owner's gate).** A future ADR-B00X stating the trigger
(e.g., provider policy change, C5 residual risk realized, throughput ceiling),
approved by the owner, then: place the existing keys per BA-3 (proxy env only;
verify funding and limits first) → execute B2.2 → flip `policies.yaml` to
`mode: P` in the same PR. Nothing else moves; this is the config migration §81
was built for.
