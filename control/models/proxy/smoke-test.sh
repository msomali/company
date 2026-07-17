#!/usr/bin/env bash
# B2.2 acceptance (H-EXEC, conditional on Mode P reactivation ADR — ADR-B003):
# one call per §81 policy through the proxy. Paste output into the B2.2
# evidence commit. Never prints key material.
set -euo pipefail

PROXY_URL="${PROXY_URL:-http://127.0.0.1:4000}"
: "${LITELLM_MASTER_KEY:?source /etc/company/proxy.env first}"

fail=0
for policy in reasoning-max standard economy; do
  echo "== policy: $policy"
  if curl -sS --fail -X POST "$PROXY_URL/v1/chat/completions" \
      -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"$policy\",
        \"max_tokens\": 16,
        \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: ok\"}]
      }" | python3 -c 'import json,sys; r=json.load(sys.stdin); print("model:", r.get("model"), "| usage:", r.get("usage"))'; then
    echo "PASS $policy"
  else
    echo "FAIL $policy"
    fail=1
  fi
done

# consistency check: agents map here vs policies.yaml (keys-bootstrap drift guard)
python3 - <<'EOF'
import re, sys, yaml
pol = yaml.safe_load(open("control/models/policies.yaml"))["agents"]
sh = open("control/models/proxy/keys-bootstrap.sh").read()
script = dict(re.findall(r"\[(\w+)\]=([\w-]+)", sh))
if pol != script:
    print("FAIL agents map drift between policies.yaml and keys-bootstrap.sh:")
    print("  policies.yaml only:", {k: v for k, v in pol.items() if script.get(k) != v})
    print("  keys-bootstrap only:", {k: v for k, v in script.items() if pol.get(k) != v})
    sys.exit(1)
print("PASS agents map consistent (13 agents)")
EOF

exit $fail
