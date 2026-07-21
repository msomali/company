#!/usr/bin/env bash
# bootstrap-verify.sh — standing verification that the bootstrap foundation is
# intact (owner-requested 2026-07-20, post-§87 declaration).
#
# Repo-state checks ONLY. This script never touches credentials and never makes
# a network call — token validity is a runtime/rotation concern, not a
# bootstrap-integrity one. Safe to run anytime, by anyone, on a clean checkout.
#
#   bootstrap-verify.sh          verify the repo the script lives in
#   BOOTSTRAP_VERIFY_ROOT=/path bootstrap-verify.sh   verify an arbitrary tree
#                                                     (used by the test fixtures)
#
# Output (§ item 7): every check prints "PASS <label> — <what>" or
# "FAIL <label> — <why>". Exit 0 = all green; exit 1 = at least one FAIL.
#
# N/A rule (checklist item 1): a BOOTSTRAP-PLAN task written "- [ ]" counts as
# satisfied ONLY if its line carries BOTH an explicit "N/A" token AND a §87
# disposition reference ("section-87" or "§87"). A bare unchecked box always
# FAILS. This is deliberately fail-safe: it distinguishes "not done" from
# "conditionally N/A, dispositioned at §87" (e.g. B2.2, Mode P dormant) without
# ever letting a genuinely-incomplete task pass by omission.
set -uo pipefail

ROOT="${BOOTSTRAP_VERIFY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

fail_count=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; fail_count=$((fail_count + 1)); }
info() { printf '      %s\n' "$*"; }

# ---- Check 1: BOOTSTRAP-PLAN tasks complete (N/A-aware) --------------------
check_plan() {
  local label="[1/6] BOOTSTRAP-PLAN tasks"
  local plan="$ROOT/BOOTSTRAP-PLAN.md"
  if [[ ! -f "$plan" ]]; then fail "$label — missing $plan"; return; fi

  local n_done=0 n_na=0 n_incomplete=0 id
  local -a incomplete_ids=()
  while IFS= read -r line; do
    id=$(sed -nE 's/^- \[[ x]\] (B[0-9]+\.[0-9]+).*/\1/p' <<<"$line")
    [[ -z "$id" ]] && continue
    if [[ "$line" == "- [x] "* ]]; then
      n_done=$((n_done + 1))
    elif grep -qi 'N/A' <<<"$line" && grep -qiE 'section-87|§87' <<<"$line"; then
      n_na=$((n_na + 1))
      info "N/A: $id (dispositioned at §87)"
    else
      n_incomplete=$((n_incomplete + 1))
      incomplete_ids+=("$id")
    fi
  done < <(grep -E '^- \[[ x]\] B[0-9]+\.[0-9]+' "$plan")

  if (( n_done + n_na + n_incomplete == 0 )); then
    fail "$label — no task lines found in $plan"
  elif (( n_incomplete == 0 )); then
    pass "$label — ${n_done} done, ${n_na} N/A, 0 incomplete"
  else
    fail "$label — ${n_incomplete} incomplete (not done, not N/A-dispositioned): ${incomplete_ids[*]}"
  fi
}

# ---- Check 2: §85 hardening — 9 rows, all [x], zero open -------------------
check_hardening() {
  local label="[2/6] §85 hardening"
  local f="$ROOT/control/sops/hardening-evidence.md"
  if [[ ! -f "$f" ]]; then fail "$label — missing $f"; return; fi
  # A data row starts with "| <n> |" and its final cell is the Done box.
  local rows done_rows open_rows
  rows=$(grep -cE '^\|[[:space:]]*[0-9]+[[:space:]]*\|' "$f")
  done_rows=$(grep -cE '^\|[[:space:]]*[0-9]+[[:space:]]*\|.*\|[[:space:]]*\[x\][[:space:]]*\|[[:space:]]*$' "$f")
  open_rows=$(grep -cE '^\|[[:space:]]*[0-9]+[[:space:]]*\|.*\|[[:space:]]*\[ \][[:space:]]*\|[[:space:]]*$' "$f")
  if (( rows == 9 && done_rows == 9 && open_rows == 0 )); then
    pass "$label — 9/9 rows [x], 0 open"
  else
    fail "$label — expected 9 rows all [x], 0 open; got rows=${rows} done=${done_rows} open=${open_rows}"
  fi
}

# ---- Checks 3 & 4: required artifacts present ------------------------------
check_file() { # $1=label  $2=repo-relative path
  if [[ -f "$ROOT/$2" ]]; then pass "$1 — present: $2"; else fail "$1 — missing: $2"; fi
}

# ---- Check 5: dry-run episode CLOSED and complete -------------------------
check_episode() {
  local label="[5/6] dry-run episode (TASK-001)"
  local m="$ROOT/projects/PROJECT-000/episodes/TASK-001/manifest.yaml"
  if [[ ! -f "$m" ]]; then fail "$label — missing $m"; return; fi
  local closed=no complete=no
  grep -qE '^final_state:[[:space:]]*CLOSED[[:space:]]*$' "$m" && closed=yes
  grep -qE '^[[:space:]]+complete:[[:space:]]*true[[:space:]]*$' "$m" && complete=yes
  if [[ "$closed" == yes && "$complete" == yes ]]; then
    pass "$label — final_state: CLOSED, complete: true"
  else
    fail "$label — final_state:CLOSED=${closed}, complete:true=${complete}"
  fi
}

# ---- Check 6: the six TASK-001 gate records (project-scoped) --------------
check_gates() {
  local label="[6/6] TASK-001 gate records"
  local dir="$ROOT/projects/PROJECT-000/gates"
  local -a roles=(SAT SSE DPC DCE PJM HUMAN) missing=() notapproved=()
  local role f
  for role in "${roles[@]}"; do
    f="$dir/GATE-TASK-001-${role}-1.yaml"
    if [[ ! -f "$f" ]]; then
      missing+=("$role")
    elif ! grep -qE '^decision:[[:space:]]*APPROVED[[:space:]]*$' "$f"; then
      notapproved+=("$role")
    fi
  done
  if (( ${#missing[@]} == 0 && ${#notapproved[@]} == 0 )); then
    pass "$label — 6/6 present, all decision: APPROVED (projects/PROJECT-000/gates/)"
  else
    (( ${#missing[@]} )) && fail "$label — missing: ${missing[*]}"
    (( ${#notapproved[@]} )) && fail "$label — present but not APPROVED: ${notapproved[*]}"
  fi
}

printf '== bootstrap-verify == root: %s\n' "$ROOT"
check_plan
check_hardening
check_file "[3/6] Phase-1 declaration (§87)" "control/registers/section-87-phase-1-declaration.md"
check_file "[4/6] B8.1 rotation evidence"    "control/registers/section-b8.1-rotation-evidence.md"
check_episode
check_gates

if (( fail_count == 0 )); then
  printf '\nGREEN — bootstrap foundation intact (0 failures)\n'
  exit 0
fi
printf '\nRED — %d check(s) failed\n' "$fail_count"
exit 1
