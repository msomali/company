# BOOTSTRAP-PLAN — single source of progress truth (BA-5.5)

Task definitions, dependencies, actors, and outputs: **Bootstrap Annex BA-6** (authoritative).
Rules of execution: BA-5. Prohibitions: BA-2. One task = one branch = one PR.

- [x] B0.1 (H) Hardening §85 complete, evidence committed — `control/sops/hardening-evidence.md` (owner-attested 2026-07-15; all 9 §85 rows now `[x]` — row 9 kill-switch drill closed 2026-07-17, row 4 egress allowlist closed 2026-07-20 via PR #76)
- [x] B0.2 (H) Forge org, machine accounts, tokens placed per BA-3 — repo + `agenticfoundrybot` live; PAT placement per ADR-B002 (classic PAT deviation recorded in evidence row 6)
- [x] B0.3 (H) Provider subscriptions confirmed + OAuth sign-ins done (D5 resolved per ADR-B003); policies.yaml (mode: S) + prices.yaml filled — PR #6 merged 2026-07-16
- [x] B0.4 (H) §51 owner + channel filled; §86 register signed — PR #16 merged 2026-07-17 (tick predated artifact; provenance recorded in PR #16 §5 and lesson L-001)
- [x] B1.1 (A) Repo initialized with this kit; digest extracted — PR #3 merged 2026-07-16
- [x] B1.2 (H-EXEC) Branch protection + CODEOWNERS + required checks applied — spec PR #4; Phase 1 evidence PR #5; CODEOWNERS PR #7 (ADR-B005); Phase 2 checks row closes with B1.3
- [x] B1.3 (A) CI: frontmatter-lint, handoff-check, secret-scan implemented and green — PR #8 merged 2026-07-16; checks required+strict (B1.2 Phase 2, PR #9)
- [x] B2.1 (A) LiteLLM compose/config authored (dormant Mode P fallback; secret names only) — PR #10 merged 2026-07-16 (tick restored by L-001 audit; original tick claimed in 67ad1502 but never landed)
- [ ] B2.2 (H-EXEC) CONDITIONAL — only on Mode P reactivation ADR; else mark N/A-dormant at §87
- [x] B3.1 (A) Manifest generator + tests — PR #11 merged 2026-07-16 (tick restored by L-001 audit; original tick claimed in 67ad1502 but never landed)
- [x] B3.2 (A) 13 manifests authored; agent files generated (NOT activated) — PR #12 merged 2026-07-16
- [x] B4.1 (A) task-create + schemas/task.json + rejection tests — PR #13 merged 2026-07-16
- [x] B4.2 (A) Dispatcher per §82 + tests — PR #14 (core) + PR #15 (approvals/metering) merged 2026-07-17
- [x] B4.3 (H-EXEC) Dispatcher systemd unit installed under `dispatcher` user — spec PR #17; owner install evidence + deploy-key rider PR #20; rider fold PR #18 (all merged 2026-07-17)
- [x] B4.4 (A) Episode collector + kill-switch script — PR #19 merged 2026-07-17; hardening row 9 stays open until the owner runs `control/sops/killswitch-drill.md` (row closes on the drill, not the merge — owner direction 2026-07-17)
- [x] B5.1 (A) Eval runner + golden tasks (PJM, SDE, SAT, DCE); seeded failure blocks — PR #22 merged 2026-07-17
- [x] B5.2 (A) Gate-writer CI emits gates/GATE-*.yaml on merge — PRs #23/#24/#25 merged 2026-07-17; live demo + #23/#24 backfills recorded (gates/), recursion guard held
- [x] B6.1 (A) /memory tree + gated write path + purge script — PR #27 merged 2026-07-17 (seed record MEM-ORG-0001)
- [x] B6.2 (A) SOPs finalized — incident, skill-review, advisory-review finalized; PR #29 merged 2026-07-18
- [x] B6.3 (A) Weekly metrics script + first report — `metrics_weekly.py` (§78-26) + `company/metrics/METRICS-2026-W29.md` (APPROVED); PR #31 merged 2026-07-18
- [x] B7.1 (H) PROJECT-000 charter signed — PR #49 merged 2026-07-18 (`status: APPROVED`, budget ceiling USD 50)
- [x] B7.2 (J) Dry run §88 checks 1–5, 7, 10–14 — evidenced in the TASK-001/TASK-002 episode; PR #58 merged 2026-07-19 (merge `e5d18e4`)
- [x] B7.3 (H) Dry run §88 checks 6, 8, 9 — evidenced in the same episode; PR #58 merged 2026-07-19
- [x] B7.4 (J) Phase 1 declared per §87; friction converted — `control/registers/section-87-phase-1-declaration.md` (this PR); §88 14/14; B7.4 backlog dispositioned
- [ ] B8.1 (H) Bootstrap identity revoked; tokens rotated — post-declaration owner act (BA-6); agent activation remains a separate human act (BA-2.4)
