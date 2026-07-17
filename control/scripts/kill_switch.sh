#!/usr/bin/env bash
# Kill switch (B4.4) — v2 §78 row 28 / §88 check 13. Mode S primary
# (ADR-B003); Mode P steps auto-skip unless the proxy is running.
#
#   kill_switch.sh pause  [--dry-run]   halt everything, revoke model access,
#                                       freeze main, preserve evidence
#   kill_switch.sh resume [--dry-run]   undo pause (services back; UNFREEZE is
#                                       a deliberate manual admin act)
#   kill_switch.sh status               show what is up/down/frozen
#
# Run as root on the host. Every action logs to $EVIDENCE_DIR/kill-switch.log.
# Design: best-effort, ordered, idempotent — a partially-failed pause can be
# re-run; steps report DONE/SKIP/FAIL and the script continues (an incident
# is not the moment to die on step 2 of 7).
set -uo pipefail

MODE="${1:?usage: kill_switch.sh pause|resume|status [--dry-run]}"
DRY="${2:-}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPO_DIR="${REPO_DIR:-/srv/company/repo}"
EVIDENCE_DIR="${EVIDENCE_DIR:-/var/company/incident-$STAMP}"
GH_REPO="${GH_REPO:-msomali/company}"

run() {  # run "<description>" cmd...
  local desc="$1"; shift
  if [ "$DRY" = "--dry-run" ]; then
    echo "PLAN  $desc :: $*"
    return 0
  fi
  if "$@" >>"$EVIDENCE_DIR/kill-switch.log" 2>&1; then
    echo "DONE  $desc"
  else
    echo "FAIL  $desc (continuing — see kill-switch.log)"
  fi
}

pause() {
  [ "$DRY" = "--dry-run" ] || mkdir -p "$EVIDENCE_DIR"
  echo "== kill switch PAUSE $STAMP (mode S primary; dry=${DRY:-no})"

  # 1. stop dispatch — no new work enters the system
  run "1. stop dispatcher service" systemctl stop company-dispatcher.service

  # 2. stop agent sessions/containers (OpenClaw sandboxes are docker containers)
  run "2. stop company docker containers" \
      bash -c 'docker ps -q --filter "name=openclaw" | xargs -r docker stop'

  # 3. revoke model access — Mode S: stop the gateway (auth profiles die with it)
  run "3. stop OpenClaw gateway (Mode S revocation)" \
      bash -c 'command -v openclaw >/dev/null && sudo -u mr-robot openclaw gateway stop || systemctl stop openclaw-gateway.service'

  # 3b. Mode P (only if the proxy is actually running): suspend + down
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q litellm; then
    run "3b. stop Mode P proxy containers" \
        bash -c 'cd "$REPO_DIR/control/models/proxy" && docker compose --profile mode-p down'
  else
    echo "SKIP  3b. Mode P proxy not running (dormant per ADR-B003)"
  fi

  # 4. sever dispatcher push access (deploy key — owner rider, PR #17/#18)
  run "4. revoke dispatcher deploy key on repo (admin token required)" \
      bash -c 'gh repo deploy-key list --repo "'"$GH_REPO"'" --json id,title \
        --jq ".[] | select(.title==\"company-dispatcher\") | .id" \
        | xargs -r -I{} gh repo deploy-key delete {} --repo "'"$GH_REPO"'"'

  # 5. freeze main (protection lock; admin token required)
  run "5. freeze protected branch main" \
      bash -c 'gh api -X PUT "repos/'"$GH_REPO"'/branches/main/protection" \
        --input "'"$REPO_DIR"'/control/sops/protection-frozen.json"'

  # 6. preserve evidence — episodes, logs, journal
  run "6. archive episodes + logs" \
      bash -c 'tar czf "$0/episodes-$1.tgz" -C "$2" projects --ignore-failed-read; \
               journalctl -u company-dispatcher.service --no-pager > "$0/dispatcher-journal.txt" 2>/dev/null || true' \
      "$EVIDENCE_DIR" "$STAMP" "$REPO_DIR"

  # 7. incident marker (INCIDENT.md SOP takes over from here)
  if [ "$DRY" = "--dry-run" ]; then
    echo "PLAN  7. write incident marker $EVIDENCE_DIR/INCIDENT-MARKER"
  else
    printf 'incident: %s\npaused_by: %s\nsop: control/sops/incident.md\n' \
      "$STAMP" "$(whoami)" > "$EVIDENCE_DIR/INCIDENT-MARKER"
    echo "DONE  7. incident marker written"
  fi
  echo "== PAUSE complete. Next: control/sops/incident.md. Resume is a"
  echo "   deliberate act: kill_switch.sh resume (unfreeze stays manual)."
}

resume() {
  echo "== kill switch RESUME $STAMP (dry=${DRY:-no})"
  echo "NOTE: main unfreeze + deploy-key re-registration are deliberate admin"
  echo "      acts — commands printed, not executed:"
  echo "      gh api -X PUT repos/$GH_REPO/branches/main/protection --input control/sops/protection-normal.json"
  echo "      gh repo deploy-key add /srv/company/.ssh/dispatcher_deploy_key.pub --repo $GH_REPO --title company-dispatcher --allow-write"
  run "1. start OpenClaw gateway" \
      bash -c 'command -v openclaw >/dev/null && sudo -u mr-robot openclaw gateway start || systemctl start openclaw-gateway.service'
  run "2. start dispatcher service (re-dispatches from state.yaml)" \
      systemctl start company-dispatcher.service
  echo "== RESUME issued. Verify: kill_switch.sh status"
}

status() {
  echo "== kill switch STATUS"
  systemctl is-active company-dispatcher.service 2>/dev/null | sed 's/^/dispatcher: /'
  (command -v openclaw >/dev/null && sudo -u mr-robot openclaw gateway status 2>/dev/null | head -3) || echo "gateway: unknown"
  docker ps --format 'container up: {{.Names}}' 2>/dev/null | grep -Ei 'openclaw|litellm' || echo "containers: none running"
}

case "$MODE" in
  pause) pause ;;
  resume) resume ;;
  status) status ;;
  *) echo "usage: kill_switch.sh pause|resume|status [--dry-run]"; exit 2 ;;
esac
