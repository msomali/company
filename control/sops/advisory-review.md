# Weekly Advisory Review SOP — v2.1 §85.1 (finalized B6.2)

**Cadence:** every Monday, human owner (sole host/credential holder).
**Rule:** a missed week is a Medium finding — log it in the table as its own
row. The CVE floor (row 1 of hardening evidence: fixes for CVE-2026-25253
and CVE-2026-32922) is a minimum marker, not the bar; the current advisory
stream is.

## Sources (check in order)

1. OpenClaw releases + security advisories (GitHub `openclaw/openclaw`
   releases page and repository security advisories).
2. Claude Code CLI release notes (documented dependency, BA-4 rev 1.2).
3. OS security: `apt update && apt list --upgradable` /
   unattended-upgrades log on the VM.
4. Python deps used by control scripts (pyyaml, jsonschema, pytest — GitHub
   advisory DB via `pip index` or release pages; no auto-upgrade).
5. Provider policy/terms changes (feeds §86-C5 — any change triggers the
   register's on-change review, not just the quarterly one).

## Per-review steps

1. Record installed vs latest: `openclaw --version`, `claude --version`.
2. Scan each source for items affecting installed versions or configuration
   (gateway exposure, sandbox escapes, credential handling, CI actions).
3. Decide **hold** or **upgrade** per item; upgrades to OpenClaw follow the
   version-floor rule (latest stable; record exact version + date). An
   advisory that is actively exploited against a running component →
   `control/sops/incident.md`, not a table row.
4. Append the log row (evidence links, not prose claims).
5. If configuration changed (bind address, versions, tokens), re-verify the
   affected hardening-evidence rows and note it in the row's evidence cell.

## Review log

| Date | Reviewer | Findings | Decision | Evidence |
|---|---|---|---|---|
| 2026-07-15 | msomali | Baseline at provisioning: OpenClaw 2026.7.1 (2d2ddc4), latest stable; subsumes CVE floor | hold (current) | hardening-evidence row 1 |
