# Dispatcher Install Spec — B4.3 (H-EXEC)

Bootstrap prepares (this file + the unit + the runtime); the human executes on
the host and pastes evidence below (BA-5.4). Runtime = BA-1.4: systemd service,
OS user `dispatcher`, outside OpenClaw.

## What gets installed

| Piece | Source | Destination |
|---|---|---|
| Repo checkout | `msomali/company` | `/srv/company/repo` (owned `dispatcher:dispatcher`) |
| Python venv | python3 + pyyaml + jsonschema | `/srv/company/venv` |
| Unit file | `control/sops/systemd-company-dispatcher.service` | `/etc/systemd/system/company-dispatcher.service` |
| Env file | created by you, from the names below | `/etc/company/dispatcher.env` (root:dispatcher, 640) |

Env file variable NAMES (values never in the repo — SECRETS-MANIFEST):
`GH_TOKEN_DISPATCHER` — **RETIRED** by the deploy-key rider (PR #17 review,
executed PR #20): the dispatcher authenticates by its dedicated deploy key
only, never a PAT. Do not provision this variable.
`APPROVALS_CHANNEL_TOKEN` (reserved until the dedicated channel exists — §51
register pre-notes that adding it amends the register + sets the OpenClaw
command owner). The env file remains empty until then (evidence, PR #20).

## Design decisions — APPROVED by owner (PR #17 review, 2026-07-17) with the deploy-key rider

1. **State-commit identity (APPROVED).** Episode/state commits made by the
   dispatcher are authored as `dispatcher <dispatcher@company.local>` — NOT
   the bot PAT identity. ADR-B000 binds *agent* commits to `agenticfoundrybot`;
   the dispatcher is infrastructure (BA-1.4). The provenance ledger is
   three-way: owner / agent-roles / infrastructure.

   **Owner rider — authentication separation (binding):** the dispatcher
   pushes with its **own dedicated read-write deploy key** (ed25519, generated
   at install, key file mode 600 under the `dispatcher` user, registered on
   `msomali/company`) — **NEVER a third copy of the bot PAT.** Rationale
   (owner): independent revocation — the B4.4 kill switch cuts dispatcher
   access without touching agent pushes; no PAT custody proliferation; GitHub
   attributes pushes to the key. Custody row added to SECRETS-MANIFEST.
2. **Push path (APPROVED).** The dispatcher never pushes to `main` (protection
   applies to everyone). It commits state/episode changes locally and pushes
   to `dispatch/TASK-###` branches; episode artifacts enter `main` via the
   task's PR like everything else. This satisfies §79 ("episodes/ writable
   only by CI" on main) without weakening protection. If you prefer episodes
   to land exclusively via CI automation later, the gate-writer (B5.2)
   absorbs it.

**Read-path note (owner):** review-polling and fetches can run
unauthenticated while the repo is public (ADR-B004). **TODO at the private
flip:** provision a read credential for the dispatcher (the deploy key
already covers it — verify, then delete this line).

## Install (run as root; each command idempotent)

```bash
# 1. user + directories
useradd --system --create-home --home-dir /srv/company --shell /usr/sbin/nologin dispatcher || true
install -d -o dispatcher -g dispatcher /srv/company

# 2. checkout + venv (as dispatcher)
sudo -u dispatcher git clone https://github.com/msomali/company /srv/company/repo || \
  sudo -u dispatcher git -C /srv/company/repo pull --ff-only
sudo -u dispatcher python3 -m venv /srv/company/venv
sudo -u dispatcher /srv/company/venv/bin/pip install pyyaml jsonschema

# 3. dispatcher git identity (design decision 1)
sudo -u dispatcher git -C /srv/company/repo config user.name  "dispatcher"
sudo -u dispatcher git -C /srv/company/repo config user.email "dispatcher@company.local"

# 3b. dedicated deploy key (owner rider, PR #17) — never the bot PAT
sudo -u dispatcher install -d -m 700 /srv/company/.ssh
sudo -u dispatcher ssh-keygen -t ed25519 -N "" -C "company-dispatcher-deploy" \
  -f /srv/company/.ssh/dispatcher_deploy_key      # creates key 600 by default
# Register the PUBLIC key as a read-write deploy key (admin, one-time):
#   gh repo deploy-key add /srv/company/.ssh/dispatcher_deploy_key.pub \
#     --repo msomali/company --title company-dispatcher --allow-write
# (or Settings → Deploy keys → Add; check "Allow write access")
sudo -u dispatcher git -C /srv/company/repo remote set-url origin \
  git@github.com:msomali/company.git
sudo -u dispatcher git -C /srv/company/repo config core.sshCommand \
  "ssh -i /srv/company/.ssh/dispatcher_deploy_key -o IdentitiesOnly=yes"
# Revocation drill target (B4.4 kill switch): deleting the deploy key on the
# repo severs dispatcher push access without touching agent credentials.

# 4. env file (names only here; you supply values if/when needed)
install -d -m 755 /etc/company
touch /etc/company/dispatcher.env
chown root:dispatcher /etc/company/dispatcher.env && chmod 640 /etc/company/dispatcher.env

# 5. unit
cp /srv/company/repo/control/sops/systemd-company-dispatcher.service \
   /etc/systemd/system/company-dispatcher.service
systemctl daemon-reload
systemctl enable --now company-dispatcher.service
```

## Verify (paste output into Evidence below)

```bash
systemctl status company-dispatcher.service --no-pager | head -12
journalctl -u company-dispatcher.service -n 5 --no-pager
sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/dispatcher_runtime.py --once
```

Additional rider verification (paste with the rest):

```bash
sudo -u dispatcher git -C /srv/company/repo ls-remote origin HEAD | head -1   # deploy key works (read)
stat -c '%a %U' /srv/company/.ssh/dispatcher_deploy_key                        # expect: 600 dispatcher
```

Expected: service `active (running)`; journal shows the idle heartbeat
(`dispatcher: 0 task(s); concurrency cap=3`); `--once` exits 0. The loop is
deliberately idle during bootstrap — every manifest is contract-only, so
dispatch structurally refuses (BA-2.4); the service existing and surviving
restart is the B4.3 acceptance, not task throughput.

## Manual smoke (optional, no side effects)

```bash
echo "APPROVE TASK-999 SAT" | sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/dispatcher_runtime.py \
  --process-review --project PROJECT-000 --approver msomali --reference manual-smoke
# expected: "refused: ... unknown task TASK-999" — proves parse+authorize
# work and that nothing is invented for nonexistent tasks.
```

## Evidence — B4.3 (owner paste + date)

● company-dispatcher.service - Company dispatcher (v2 §82) — task state, approvals, metering
     Loaded: loaded (/etc/systemd/system/company-dispatcher.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-07-17 01:24:44 PDT; 7h ago
 Invocation: 7d629884fde64f74833fee931792b391
       Docs: file:///srv/company/repo/control/sops/dispatcher-install.md
   Main PID: 69993 (python)
      Tasks: 1 (limit: 4484)
     Memory: 18.8M (max: 1G, available: 1005.1M, peak: 23.1M)
        CPU: 657ms
     CGroup: /system.slice/company-dispatcher.service
             └─69993 /srv/company/venv/bin/python control/scripts/dispatcher_runtime.py --daemon --interval 60

Jul 17 01:24:44 mr-robot-VMware20-1 systemd[1]: Started company-dispatcher.service - Company dispatcher (v2 §82) — task state, approvals, metering.

dispatcher: 0 task(s); concurrency cap=3

Deploy-key rider executed per PR #17 review: key "dispatcher@company-vm" registered read-write <date>; GH_TOKEN_DISPATCHER retired — dispatcher authenticates by key only
Identity verification: ssh -T as dispatcher greets "Hi msomali/company!" — deploy-key scoped identity confirmed, 2026-07-17.

Attested by: msomali, 2026-07-17

## Addendum — session-spawn activation pre-flight (activation item 1, 2026-07-21)

The dispatcher spawns real agent turns via the `openclaw` CLI against the
loopback gateway (`control/scripts/session_backend.py`; one spawn = one agent
turn, `openclaw agent --json`). Model credentials never leave the gateway
user (Mode S, ADR-B003) — the dispatcher carries ONLY the gateway connection
token. Everything below is OWNER-executed on activation day, in order,
BEFORE the first one-shot.

### PREREQUISITE 1 — system-wide openclaw CLI (hard requirement)

The systemd unit runs `ProtectHome=yes`, and the `dispatcher` user gets **no
traverse rights into `/home/mr-robot`** — the home boundary stays intact
(owner ruling 2026-07-21; do NOT solve this with permissions). The CLI must
resolve from a system path:

```bash
npm install -g --prefix /usr/local openclaw
```

Resolution after install: the daemon resolves `/usr/local/bin/openclaw` via
the systemd default PATH; interactive `sudo -u dispatcher` shells resolve the
same binary. Nothing under `/home` is read by either path.

Verify (paste with pre-flight evidence — the one-shot is NOT run until this
passes):

```bash
sudo -u dispatcher which openclaw     # expect: /usr/local/bin/openclaw
sudo -u dispatcher openclaw --version # version prints, no error
```

### PREREQUISITE 2 — gateway token in the env file

Append to `/etc/company/dispatcher.env` (root:dispatcher 640; names in
SECRETS-MANIFEST — same secret as gateway auth, second destination):

```
OPENCLAW_GATEWAY_TOKEN=<gateway token value>
# seat config — REQUIRED for agent-id resolution (see PREREQUISITE 3):
OPENCLAW_CONFIG_PATH=/etc/company/openclaw-dispatcher.json
# optional — defaults to ws://127.0.0.1:18789 in session_backend.py
# OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
```

Coupling (deliberate, owner ruling 2026-07-21): rotating the gateway token
severs dispatcher spawn access and dashboard login together — see the
killswitch-drill SOP note. Spawn pre-flight refuses when the variable is
absent; nothing is spawned on a refusal.

### PREREQUISITE 3 — the 13 role agents, applied to BOTH seats

**Why two seats (corrected 2026-07-21 after the first live-spawn failure):**
the `openclaw` CLI validates `--agent` against the **invoking user's own
config** before it ever contacts the gateway
(`src/commands/agent-via-gateway.ts`: unknown ids throw
`Unknown agent id "…"` client-side). The dispatcher's fresh default config
knew only `main`, so both live one-shots refused while the dry-run (no
gateway contact) stayed green. "Configured in gateway agents.list" is
necessary but NOT sufficient: the gateway seat executes; the dispatcher
seat resolves.

Generate ONE artifact, apply it twice:

```bash
python3 control/scripts/agents_config_gen.py --out /tmp/company-agents.json5

# Seat 1 — gateway (execution): merge agents.list into the gateway user's
# ~/.openclaw/openclaw.json (workspaces, models, containment; validate
# config, restart gateway — your standing pre-restart validator step).

# Seat 2 — dispatcher (id resolution): install the SAME file VERBATIM — it
# is a complete, valid JSON5 config document — then point the CLI at it
# via OPENCLAW_CONFIG_PATH (PREREQUISITE 2 env block):
install -o root -g dispatcher -m 640 /tmp/company-agents.json5 \
  /etc/company/openclaw-dispatcher.json
```

On the dispatcher seat the `workspace`/`model` fields are inert — only the
ids resolve; execution state stays with the gateway. No traverse into
`/home/mr-robot` is needed or permitted (standing ruling); device/pairing
state still lives in the dispatcher's own `~/.openclaw` (`/srv/company`).

The header carries provenance (source policies.yaml commit + date +
DO-NOT-HAND-EDIT): host config has no CI lint, so **regenerate after any
policies.yaml change and re-apply to BOTH seats; never hand-edit either
applied copy**. Each agent's gateway-side `workspace` must contain that
role's AGENTS.md from `control/manifests/_generated/<ROLE>/` (paths
adjustable; ids are not — the dispatcher spawns `agent_id = role.lower()`).
Fallbacks are explicit per entry: `agents.list[].model` without `fallbacks`
is STRICT (no fallback at all — docs concepts/model-failover); the explicit
pair is what makes a rate-limited primary fail over inside the runtime per
MODEL-002.

**Seat-check (verify BOTH, paste with pre-flight evidence — this check
would have caught the 2026-07-21 failure before any live attempt):**

```bash
# dispatcher seat — must list sde (and the other 12 ids),
# NOT just "main (default)":
sudo -u dispatcher bash -c 'set -a; . /etc/company/dispatcher.env; set +a; \
  openclaw agents list'

# gateway seat — same ids visible to the gateway user:
sudo -u mr-robot -i openclaw agents list
```

**Per-agent store permissions (differential confirmed 2026-07-21):** agent
dirs under the gateway user's `~/.openclaw/agents/<id>/` that the runtime
**auto-creates at first spawn** come up **775**; the human-provisioned
Phase-0 store (`bootstrap`) is **700**. The dir holds that agent's auth
store (`openclaw-agent.sqlite` — model credentials; SECRETS-MANIFEST
Mode S note). After provisioning — or after the first spawn of any newly
activated agent — tighten and verify on the gateway seat:

```bash
sudo -u mr-robot -i sh -c 'chmod 700 ~/.openclaw/agents/<id>'
sudo -u mr-robot -i sh -c 'stat -c "%a %U" ~/.openclaw/agents/<id>'
# expect: 700 mr-robot — anything wider is a finding; paste with evidence
```

### AUTH-PROVISIONING — fleet credentials live in `main`'s store (corrected 2026-07-22; supersedes the 2026-07-21 revision)

**Semantics (differential 2026-07-22, pinned to source at the installed build
v2026.7.1 / 2d2ddc43).** Model auth resolves **per profile id: the agent's own
store first, then the `main` agent's store**
(`~/.openclaw/agents/main/agent/openclaw-agent.sqlite`) — the literal id
`main`, ALWAYS, independent of `default: true` marking or `agents.list` order.
The runtime inheritance base is resolved with an **empty config**:
`resolveAuthStorePath()` → `resolveDefaultAgentDir({})` → `"main"`
(`src/agents/auth-profiles/path-resolve.ts`,
`src/agents/auth-profiles/store.ts` `loadAuthProfileStoreForRuntime`;
`DEFAULT_AGENT_ID = "main"` in `src/routing/session-key.ts:32`; behavior
locked by `oauth.fallback-to-main-agent.test.ts`). An agent-local profile with
the same id SHADOWS main's (merge override precedence,
`mergeAuthProfileStores`). `main` need NOT be a configured agent — a
store-only `main` inherits fine (our deployment). The previous revision of
this block ("default agent's store — `default: true`, else `agents.list[0]`,
else `main`") was WRONG about the read-through base: `resolveDefaultAgentId(cfg)`
governs which store the CLI **writes** when `--agent` is omitted
(`src/commands/models/auth.ts` `resolveModelsAuthAgentDir`), not which store
the runtime **inherits** from. Sharing via read-through is the documented
design (`docs/auth-credential-semantics.md`: non-portable profiles "remain
available through read-through inheritance"; the cross-agent OAuth refresh
lock exists precisely so N agents can share one profile).

**Two write-targeting traps (both confirmed live 2026-07-22):**

1. The bare no-`--agent` form writes the **configured default agent's** store
   (bootstrap today) — a store nothing inherits from. Consistent with how the
   live Anthropic token got stranded in bootstrap's store while all 13 role
   agents read main's dead one.
2. `--agent main` is REJECTED while `main` is absent from `agents.list`
   (`Unknown agent id "main"` — `resolveKnownAgentId` validates against
   `listAgentIds`, which only implies `main` when the list is EMPTY).
   Sanctioned bridge: temporarily add a minimal `{ "id": "main" }` entry for
   the duration of the write, then remove it. Never hand-edit the sqlite
   (SECRETS-MANIFEST).

**Check (BEFORE any `--live` — unchanged):**

```bash
# auth overview as THIS agent resolves it — policy primary AND fallback
# providers must report usable credentials; the `effective=profiles:` path
# shows WHICH store each provider actually resolves from:
sudo -u mr-robot -i openclaw models status --agent <id>

# optional real-call probe of the policy's provider (consumes tokens):
sudo -u mr-robot -i openclaw models status --agent <id> --probe --probe-provider anthropic
```

Auth warnings / missing-credential reasons = **STOP; no --live attempt.**
Note the static-token blind spot: a `token`-class credential with no recorded
expiry reports `static` (healthy-looking) right up until the provider rejects
it at request time — attempt 3's failure mode. The `--probe` form is the only
pre-flight that actually proves a static token alive.

**Fleet repair / rotation — ONE write to main's store (preferred; repairs
inheritance for every role agent at once). Owner-executed, gateway seat:**

```bash
# 0. baselines (paste with evidence)
sudo -u mr-robot -i openclaw models status --agent bootstrap
sudo -u mr-robot -i openclaw models status --agent sde

# 1. mint a fresh subscription token on the host (Mode S custody, ADR-B003:
#    the owner's Claude sign-in performs the mint; only the token enters the store)
claude setup-token

# 2. TEMPORARILY add { "id": "main" } to agents.list in ~/.openclaw/openclaw.json
#    (standing config-validator step applies; gateway hot-reload of an inert,
#    unbound agent is expected and harmless)

# 3. the write — interactive prompt paste (keeps the token out of argv/history);
#    overwrite the canonical profile id IN PLACE and record the documented
#    lifetime so expiry becomes visible instead of a silent 401:
sudo -u mr-robot -i openclaw models auth --agent main paste-token \
  --provider anthropic --profile-id anthropic:default --expires-in 365d

# 4. verify: store itself, then read-through, then live probe, then no-regression
sudo -u mr-robot -i openclaw models status --agent main       # new masked token at anthropic:default; openai OAuth untouched
sudo -u mr-robot -i openclaw models status --agent sde        # anthropic effective=profiles:~/.openclaw/agents/main/... with the NEW token
sudo -u mr-robot -i openclaw models status --agent sde --probe --probe-provider anthropic
sudo -u mr-robot -i openclaw models status --agent bootstrap  # unchanged (local profile shadows main)

# 5. REMOVE the temporary { "id": "main" } entry; validate; restart for
#    deterministic credential pickup across running sessions
sudo -u mr-robot -i openclaw gateway restart

# 6. store perms (the per-agent 700 line in PREREQUISITE 3 applies to main too)
sudo -u mr-robot -i sh -c 'stat -c "%a %U" ~/.openclaw/agents/main'   # expect: 700 mr-robot

# 7. sandbox-container sweep (owner finding 4a, 2026-07-22): the temporary
#    main entry can spin an agent-main sandbox as a side effect of ANY
#    gateway activity while it exists (observed 16:16 during an sde probe).
#    After entry removal + restart, check and remove:
docker ps -a --format '{{.Names}}' | grep '^openclaw-sbx-agent-main-' || echo 'none (clean)'
# for each name printed:  docker rm -f <name>   — paste the sweep output
# with the evidence either way
```

Blast radius: one profile (`anthropic:default`) replaced in place in main's
store under the store lock; the openai OAuth profile is a different profile id
and is untouched; all 13 role agents + SAT inherit immediately (read-through,
no copies); bootstrap keeps shadowing with its own live token (convergence
note below). Rollback: none needed — the replaced credential is already dead.

**Credential class (Anthropic, Mode S).** This build has NO OpenClaw-managed
Anthropic OAuth (`docs/providers/anthropic.md`: API key or Claude-CLI reuse;
for "OpenClaw-managed OAuth" the docs point at OpenAI). The subscription-
custody options are:

- **`token`/static from `claude setup-token`** — what both stores hold today
  (`token:sk-ant-o…`). Direct API calls, inheritance-friendly, subscription
  quota windows in usage tracking. **No refresh path**: it dies at provider-
  side expiry/revocation, and without a recorded `--expires-in` OpenClaw shows
  it `static`/healthy until the first 401. This is the sanctioned fleet class
  today — ALWAYS record `--expires-in` (setup-token mints are documented
  ~1 year) and calendar the renewal ~2 weeks early.
- **`--method cli` is NOT a pure auth write** — corrected from the previous
  revision, which recommended it. It mirrors the host Claude-CLI login into a
  `claude-cli`-provider profile AND patches `agents.defaults.models` to route
  `anthropic/*` through the `claude -p` subprocess runtime
  (`extensions/anthropic/register.runtime.ts`,
  `buildAnthropicCliMigrationResult`). That is a runtime-architecture
  decision (per-turn subprocess, §86-C5 Agent-SDK policy surface), not a
  credential repair. Do not use it to fix fleet auth.
- **`api-key`** — Mode P only; forbidden while Mode S is declared (ADR-B003).

Contrast for the record: the shared OpenAI profile is `oauth` class —
OpenClaw refreshes it itself (serialized by the cross-agent refresh lock),
which is why openai reports `ok expires in …` while Anthropic shows `static`.

**Steady-state rules:**

- Fleet credentials — and every rotation — are written to MAIN's store via
  the bridge above. Never the bare no-`--agent` form (trap 1); never
  per-agent for shared custody.
- Per-agent writes (`openclaw models auth --agent <id> …`, honored by `login`,
  `setup-token`, `paste-token`, `paste-api-key`, `order` — `docs/cli/models.md`)
  are the EXCEPTION, only for deliberately divergent custody (an agent on its
  own account). Any agent-local profile permanently shadows main's for that
  profile id — record it in evidence, because rotating main will NOT heal that
  agent.
- Known shadow today: bootstrap's local `anthropic:default` (live). At the
  next Anthropic rotation, rotate main's and retire bootstrap's local profile
  so custody converges to one point (2026.7.1 ships no `models auth remove`;
  `login --force` clears a provider's profiles during re-login; never
  hand-edit the sqlite).
- OpenAI-family agents and SAT need NO write — they inherit main's live OAuth
  (verified 2026-07-22). `login --provider openai --agent <id>` only for the
  divergent-custody exception.

Then re-run the check; paste check + remediation output with pre-flight
evidence. Custody stays SECRETS-MANIFEST Mode S true: stores host-side,
credentials created by human sign-in, never in the repo.

### PREREQUISITE 4 — first-connect device pairing

The dispatcher's first CLI connect may raise a one-time device-pairing
approval (gateway clients doc). Approve it (dashboard or `openclaw pairing`)
before the first one-shot, or the one-shot stalls on it.

### First live spawn — one-shot only; the daemon stays scan-only

`--daemon` NEVER dispatches: it constructs no session backend, by code. The
only spawning entrypoint is the owner-invoked one-shot:

```bash
# dry-run (default): prints role/model policy/caps/prompt hash/argv plus
# WOULD-REFUSE reasons; spawns nothing; exit 2 if anything would refuse
sudo -u dispatcher bash -c 'set -a; . /etc/company/dispatcher.env; set +a; \
  /srv/company/venv/bin/python control/scripts/dispatcher_runtime.py \
  --dispatch-once --project PROJECT-000 --task TASK-00X'

# live — same command + --live, human watching
```

Interlocks that must ALL hold before `--live` spawns: role manifest
`status: active` (owner flip, separate PR — BA-2.4), token present,
separation of duties, task not BLOCKED, concurrency slot free. Every refusal
is loud and spawns nothing.

### Live-observation list — first one-shot (observe, do not assume)

Owner requirement B (2026-07-21): run the first live one-shot under
deliberately tight caps (small `wall_clock_minutes` in the envelope) and
record:

1. **`--timeout` semantics under fallback:** total wall-time vs per-attempt
   across OpenClaw's up-to-10× overload retries and the model-fallback chain
   (docs state the retry loop, not its interaction with the CLI deadline).
   Compare actual wall time against the passed `--timeout`.
2. **Fallback visibility on a headless turn:** where the "↪️ Model
   Fallback" notice lands and whether `--json` meta reflects the
   fallback-vs-selected model.
3. **`in_flight` dedup:** a second one-shot against the same session key
   while a turn runs must surface `status: in_flight` (backend raises; no
   double spawn).
4. **Pairing friction:** whether PREREQUISITE 4 actually triggered, and
   where the approval surfaced.

Paste observations under Evidence below; they close requirement B.

## Delivery (ADR-B006) — workspace product → role branch → PR

Accepted 2026-07-22 (ADR-B006 decision record; binding requirements 1–3).
The dispatcher harvests, CI opens the PR as the bot, role workspaces stay
credential-free. Implementation: `control/scripts/harvest.py`,
`--harvest-once`, `.github/workflows/delivery.yml` (PR #103).

### Code vintage — the clone runs what is checked out (owner finding 1, 2026-07-23)

State-lane operations (TaskBranchCommitter) deliberately leave
`/srv/company/repo` checked out on `dispatch/TASK-###`. That checkout is
ALSO the code every owner-invoked command — and the daemon at start —
executes: on a branch minted before a tooling change, `control/scripts/`
REVERTS to the branch's vintage. Bit live 2026-07-23: the legacy
`dispatch/TASK-003` (minted before TaskBranchCommitter existed) carried
scripts with no harvest at all; the owner hand-synced main into the branch
(commit 046f) to run anything. Two rules:

1. **Before ANY owner-invoked runtime command**, put the clone back on
   current main:

   ```bash
   sudo -u dispatcher git -C /srv/company/repo switch main
   sudo -u dispatcher git -C /srv/company/repo pull --ff-only
   ```

   After repo updates or state-lane work, restart the daemon with the clone
   on main (`systemctl restart company-dispatcher.service`) — systemd reads
   the checkout as it is.
2. Branches MINTED by TaskBranchCommitter base on freshly **fetched
   origin/main** (pinned by `tests/test_branch_vintage.py`), so a new
   dispatch branch starts at today's scripts and legacy-style staleness
   cannot recur at creation. But the branch FREEZES there — a long-lived
   task lags as main advances (also pinned by test), and reused branches
   are never rebased. Rule 1 is therefore unconditional, not a
   legacy-branch special case.

### Envelope-author rule (binding requirement 3)

**`required_outputs` is the COMPLETE delivery manifest.** Anything not
listed does not ship — the harvest collects exactly these paths, nothing
else, and refuses the whole delivery when any entry is missing, oversized,
or escapes the workspace. Author envelopes accordingly:

- Entries are **repo-relative paths** (v1 §17.4: artifact_id =
  repo-relative path); the agent produces the same relative path inside its
  workspace. Example: `projects/PROJECT-000/src/titlecase_id.py`.
- `handoff.md` at the workspace root is a STANDING extra output (ADR-B006
  item 4): the agent's own §15 ten-section handoff, including a
  `role: <GATE>` claim line (§86-C6 — delivery branches are role-prefixed,
  so handoff_check requires the claim). It lands at
  `projects/<P>/episodes/<TASK>/handoff.md` and becomes the PR body.
- The task prompt must tell the agent both facts; envelopes whose
  `required_outputs` name artifacts the prompt never asked for are
  authoring defects and will refuse at harvest, loudly (binding req 1).
- **Front matter is STAMPED, not authored** (owner finding 6, 2026-07-23).
  The harvest strips any agent-written leading front matter from
  `handoff.md` and stamps the canonical §14 head mechanically — every
  field derives from the envelope + clock (`artifact_id` = destination
  path; `project`/`owner`/`sensitivity` from the envelope;
  `status: READY_FOR_REVIEW`; dates = harvest clock) — and schema-validates
  the result dispatcher-side before anything ships. Do NOT teach the
  front-matter schema in envelopes or acceptance criteria (the TASK-003
  iteration-5 criterion is the obsolete pattern); the agent's job is the
  ten SECTIONS plus the claim line, never the filing head. All other
  delivered `*.md` heads are pre-validated against the same schema at
  harvest — a bad head refuses the delivery episodically instead of
  reddening CI after the push.
- **Two different "role" facts, two channels** (owner finding 5,
  2026-07-23). The BODY claim line `role: <GATE>` names the gate that
  REVIEWS the PR — enum `SAT | SSE | DPC | DCE | PJM | HUMAN`
  (handoff_check CLAIMABLE; §86-C6 claim channel). The FRONT-MATTER
  `owner:` field — together with the branch prefix and the commit `Role:`
  trailer — names the role that AUTHORED the work; it is never parsed as
  a claim. While SAT is contract-only (pre-activation), **`role: HUMAN` is
  the CORRECT claim on deliveries**: the human owner is the reviewing
  gate. gate-writer's parser matches only the five bot gate roles and
  treats everything else as the HUMAN fallback, so an explicit
  `role: HUMAN` and no-claim converge on the same `gate_owner: HUMAN`
  record — stated here so nobody "fixes" the explicit claim into a bot
  role to satisfy a parser. (Sharp edge: gate-writer also accepts a bare
  `GATE-<ROLE>` marker in review/PR text — do not name-drop such markers
  in handoff prose.)

### Workspace location — dispatcher-readable root (owner decision required)

The dispatcher user has NO traverse into `/home/mr-robot` (standing ruling
2026-07-21; ProtectHome stays). Harvest therefore requires role workspaces
under a dispatcher-READABLE root. Recommended layout (owner executes;
adjust as preferred):

```bash
install -d -o mr-robot -g dispatcher -m 750 /srv/company-agents
# per role (gateway user owns/writes; dispatcher group-reads):
install -d -o mr-robot -g dispatcher -m 750 /srv/company-agents/<role_lc>
# then: regenerate agents_config_gen output with the new workspace paths
# and re-apply to BOTH seats (PREREQUISITE 3 — never hand-edit the copies);
# restart the gateway (standing validator step).

# stale-sandbox step (owner finding, 2026-07-22 migration; the 4a sweep is
# the precedent): existing role containers bake the OLD workspace path into
# their mounts and are REUSED at the next spawn — a migrated config alone
# does not fix them. Remove each role's container so the runtime recreates
# it against the new root on first spawn:
docker ps -a --format '{{.Names}}' | grep '^openclaw-sbx-agent-' || echo 'none (clean)'
# for each migrated role's container:  docker rm -f <name>
# (sde removed host-side by the owner during the 2026-07-22 migration —
# evidence with the migration paste; repeat per role as roles activate)
```

Until this is executed, `--harvest-once` cannot reach the product
(TASK-003's sits in `~/company-agents/sde`); the harvest refuses loudly on
an unreadable workspace — that refusal is the expected signal, not a
defect.

### Workspace permissions durability (owner finding 4, 2026-07-23)

Sandbox turns create workspace files **mode 600** (`mr-robot` only): the
dispatcher's group-read on the directories does not extend to new FILES,
so the next turn after any one-time `chmod` re-breaks harvest — the live
cycle proved one-time fixes do not survive. Make readability a property of
the TREE, not of the files that happen to exist today:

```bash
# RECOMMENDED — default ACLs (inherited by every future create):
setfacl -R -m g:dispatcher:rX -m d:g:dispatcher:rX /srv/company-agents/<role_lc>
getfacl /srv/company-agents/<role_lc> | grep default:group:dispatcher  # expect r-x
```

Why this beats the umask: POSIX ignores the process umask when the parent
directory carries a default ACL — the common create modes (0666/0777) then
land with `group:dispatcher` read via the ACL mask, regardless of how
restrictive the sandbox umask is. **Verify the live differential after the
next agent turn** (`getfacl <fresh file>`):

- `group:dispatcher:r--` with an effective mask ⇒ durable fix confirmed.
- `mask::---` ⇒ the writing tool explicitly requests mode 0600 at create —
  no inherited ACL can widen an explicit 0600. Fall back to a
  pre-harvest normalization step in the post-turn runbook:
  `setfacl -R -m g:dispatcher:rX /srv/company-agents/<role_lc>`
  (idempotent; run before each `--harvest-once`).

Alternative only if the sandbox runtime exposes umask configuration:
umask `027` plus `chmod g+s` (setgid) on the workspace root so new files
inherit the `dispatcher` group — same live verification applies. Whichever
path: the loud backstop is harvest itself — an unreadable input is an
EPISODIC refusal (`harvest_refused` + committed reason, ADR-B006 req 1),
never a raw traceback (finding 3 fix).

### Post-turn harvest (owner-invoked)

```bash
# after a successful turn (or standalone for a completed one like TASK-003):
sudo -u dispatcher bash -c 'set -a; . /etc/company/dispatcher.env; set +a; \
  /srv/company/venv/bin/python control/scripts/dispatcher_runtime.py \
  --harvest-once --project PROJECT-000 --task TASK-00N \
  --workspace /srv/company-agents/<role_lc> [--slug <short-slug>]'
# outcomes (ALL episodic — log.jsonl events committed to dispatch/TASK-00N):
#   harvest_pushed  → <role>/TASK-00N pushed; delivery.yml opens/updates the
#                     PR as the bot from the agent handoff
#   harvest_refused → exit 2, reason printed AND committed (binding req 1);
#                     includes secret-scan hits (binding req 2 — refused
#                     BEFORE any commit/push exists; file+pattern only,
#                     never the value)
#   harvest_error   → exit 1, infrastructure defect, same episodic record
# dispatch-once takes --workspace too: successful live turns then harvest
# automatically; without it the skip is printed loudly.
```

### Episode close — walking a delivered task to CLOSED (owner-invoked)

After the delivery PR merges, the §82.4 walk is three legs — all commands
run from the clone ON CURRENT MAIN first (Code vintage rule 1 above), all
writes land on `dispatch/TASK-###`:

```bash
RT='sudo -u dispatcher bash -c'
RUN='set -a; . /etc/company/dispatcher.env; set +a; /srv/company/venv/bin/python /srv/company/repo/control/scripts/dispatcher_runtime.py'

# LEG 1 — non-gate stretch INTAKE → QUALITY_REVIEW (--transition, one per
# edge, evidence = the artifact that proves the phase; PR/CI links are
# harvested into the episode manifest by the collector):
$RT "$RUN --transition --project PROJECT-000 --task TASK-00N \
  --to DISCOVERY --evidence 'envelope + charter refs'"
#   … then REQUIREMENTS, DESIGN, DELIVERY_PLAN, IMPLEMENTATION,
#   QUALITY_REVIEW — same form, one edge each, tighter evidence the better
#   (e.g. IMPLEMENTATION: 'delivery PR #NNN merged <sha>; CI green <run url>').

# LEG 2 — the six gates in order, ONE --process-review body (each APPROVE
# checks the task sits in that gate's expected state, writes the immutable
# GATE-TASK-00N-<gate>-# record, transitions, commits — approvals bind to
# the §51 owner identity; bot reviews never satisfy a gate):
printf '%s\n' \
  'APPROVE TASK-00N SAT — quality: <evidence>' \
  'APPROVE TASK-00N SSE — security: <evidence>' \
  'APPROVE TASK-00N DPC — privacy: <evidence>' \
  'APPROVE TASK-00N DCE — prod-readiness: <evidence>' \
  'APPROVE TASK-00N PJM — acceptance: <evidence>' \
  'APPROVE TASK-00N HUMAN — release: <evidence>' | \
$RT "$RUN --process-review --project PROJECT-000 \
  --approver msomali --reference '<PR review URL of record>'"
# Pre-activation note: the owner IS every gate (roles are contract-only);
# the HUMAN line lands the task in DEPLOYMENT.

# LEG 3 — tail DEPLOYMENT → CLOSED (--transition ×3: PRODUCTION_VERIFICATION,
# OPERATIONS_AND_FEEDBACK, CLOSED; evidence: merge sha / verification note /
# cost+feedback note).

# COLLECT — manifest + completeness, committed to the dispatch lane:
sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/episode_collector.py \
  /srv/company/repo/projects/PROJECT-000/episodes/TASK-00N
sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/episode_collector.py \
  /srv/company/repo/projects/PROJECT-000/episodes/TASK-00N --check
sudo -u dispatcher git -C /srv/company/repo add \
  projects/PROJECT-000/episodes/TASK-00N/manifest.yaml
sudo -u dispatcher git -C /srv/company/repo commit -m \
  "TASK-00N: episode manifest (B4.4 collector)"
sudo -u dispatcher git -C /srv/company/repo push origin dispatch/TASK-00N
# (transcripts: while live spawns log no model_usage events — metering
# wiring is §82.8 — §9 completeness does not demand transcripts; archiving
# the session transcript under transcripts/ anyway follows the TASK-001
# precedent and is encouraged.)

# LAND — episode state enters main via PR like everything else: bootstrap
# opens the PR from dispatch/TASK-00N (pr_open.py, ten-section body), the
# owner reviews/merges. Then: Code vintage rule 1 — clone back to main.
```

Gate-edge discipline (owner ruling 2026-07-23, structural): `--transition`
REFUSES any exit from a gate-owned state — approve and reject targets
alike — naming the owning gate and `--process-review` as the correct path;
only `--to BLOCKED` (escalation) passes. Gate records are unskippable by
construction on the runtime CLI, not by procedure. If a legitimate
non-gate exit from one of those states ever emerges, that is an approvals-
model change (ADR), not a flag.

### Deliverable verification — in the agent's sandbox (owner finding 4b)

Independent test verification runs **inside the agent's sandbox container
via `docker exec`, never host python** — the sandbox is the runtime that
produced the work; host interpreters differ and leak host state into
evidence:

```bash
docker ps --format '{{.Names}}' | grep '^openclaw-sbx-agent-<role_lc>-'
docker exec <container> sh -c 'cd /workspace && python3 -m pytest <tests> -q'
# paste the exec transcript (container name visible) with the gate evidence
```

## Evidence — session-spawn pre-flight + first one-shot (owner paste + date)

_(pending activation day)_
