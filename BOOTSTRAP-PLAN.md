# BOOTSTRAP-PLAN — single source of progress truth (BA-5.5)

Task definitions, dependencies, actors, and outputs: **Bootstrap Annex BA-6** (authoritative).
Rules of execution: BA-5. Prohibitions: BA-2. One task = one branch = one PR.

- [x] B0.1 (H) Hardening §85 complete, evidence committed — `control/sops/hardening-evidence.md` (owner-attested 2026-07-15; rows 4/9 open by progressive design, close pre-§87)
- [x] B0.2 (H) Forge org, machine accounts, tokens placed per BA-3 — repo + `agenticfoundrybot` live; PAT placement per ADR-B002 (classic PAT deviation recorded in evidence row 6)
- [ ] B0.3 (H) Provider subscriptions confirmed + OAuth sign-ins done (D5 resolved per ADR-B003); policies.yaml (mode: S) + prices.yaml filled
- [ ] B0.4 (H) §51 owner + channel filled; §86 register signed
- [ ] B1.1 (A) Repo initialized with this kit; digest extracted
- [ ] B1.2 (H-EXEC) Branch protection + CODEOWNERS + required checks applied
- [ ] B1.3 (A) CI: frontmatter-lint, handoff-check, secret-scan implemented and green
- [ ] B2.1 (A) LiteLLM compose/config authored (dormant Mode P fallback; secret names only)
- [ ] B2.2 (H-EXEC) CONDITIONAL — only on Mode P reactivation ADR; else mark N/A-dormant at §87
- [ ] B3.1 (A) Manifest generator + tests
- [ ] B3.2 (A) 13 manifests authored; agent files generated (NOT activated)
- [ ] B4.1 (A) task-create + schemas/task.json + rejection tests
- [ ] B4.2 (A) Dispatcher per §82 + tests
- [ ] B4.3 (H-EXEC) Dispatcher systemd unit installed under `dispatcher` user
- [ ] B4.4 (A) Episode collector + kill-switch script
- [ ] B5.1 (A) Eval runner + golden tasks (PJM, SDE, SAT, DCE); seeded failure blocks
- [ ] B5.2 (A) Gate-writer CI emits gates/GATE-*.yaml on merge
- [ ] B6.1 (A) /memory tree + gated write path + purge script
- [ ] B6.2 (A) SOPs finalized
- [ ] B6.3 (A) Weekly metrics script + first report
- [ ] B7.1 (H) PROJECT-000 charter signed
- [ ] B7.2 (J) Dry run §88 checks 1–5, 7, 10–14
- [ ] B7.3 (H) Dry run §88 checks 6, 8, 9
- [ ] B7.4 (J) Phase 1 declared per §87; friction converted
- [ ] B8.1 (H) Bootstrap identity revoked; tokens rotated
