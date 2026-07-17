#!/usr/bin/env bash
# Mode P per-agent virtual keys — DORMANT (ADR-B003). Run ONCE at reactivation
# (B2.2, H-EXEC), after the proxy is up. Creates 13 keys (one per agent,
# v1 §48.3 / ADR-B001) scoped to the agent's policy from ../policies.yaml,
# with monthly budget + budget tag. Secret values never printed: key material
# is written root-only to /etc/company/agent-keys/ (dispatcher reads at spawn).
set -euo pipefail

PROXY_URL="${PROXY_URL:-http://127.0.0.1:4000}"
OUT_DIR="${OUT_DIR:-/etc/company/agent-keys}"
: "${LITELLM_MASTER_KEY:?source /etc/company/proxy.env first}"
: "${AGENT_MONTHLY_BUDGET_USD:?REQUIRED-INPUT at reactivation (per-agent monthly cap, USD)}"

# agent -> policy; MUST mirror ../policies.yaml `agents:` (checked in CI? no —
# checked by smoke-test.sh at reactivation).
declare -A AGENT_POLICY=(
  [PJM]=standard [SAA]=reasoning-max [UUD]=standard [SDE]=reasoning-max
  [SAT]=standard [SSE]=reasoning-max [DPC]=standard [DCE]=standard
  [DE]=standard  [AIE]=reasoning-max [TW]=economy   [ALE]=economy
  [LIN]=economy
)

install -d -m 700 "$OUT_DIR"

for agent in "${!AGENT_POLICY[@]}"; do
  policy="${AGENT_POLICY[$agent]}"
  # models: policy + its fallback alias — router handles failover within scope
  response="$(curl -sS --fail -X POST "$PROXY_URL/key/generate" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"key_alias\": \"agent-$agent\",
      \"models\": [\"$policy\", \"$policy-fallback\"],
      \"max_budget\": $AGENT_MONTHLY_BUDGET_USD,
      \"budget_duration\": \"30d\",
      \"metadata\": {\"agent\": \"$agent\", \"budget_tag\": \"agent:$agent\"}
    }")"
  # extract key without echoing it; store 600, root-owned
  printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["key"])' \
    > "$OUT_DIR/$agent.key"
  chmod 600 "$OUT_DIR/$agent.key"
  echo "created virtual key for $agent (policy: $policy) -> $OUT_DIR/$agent.key"
done

echo "done: ${#AGENT_POLICY[@]} agent keys. Per-task budget tags are attached by"
echo "the dispatcher per request (metadata.budget_tag = task envelope model_budget_tag)."
