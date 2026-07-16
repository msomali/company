# Charter — PROJECT-001 (arf-care) — onboarding per v1 §56/§57
# PJM refines; the human owner approves by merging this file. No task work before merge.

product: >
  Multi-tenant care management platform for ARF (Adult Residential Facility) /
  Title 17 facilities: event-sourced, offline-first tablet PWA for staff,
  admin web app, family portal, FastAPI backend.
intent: onboarded (revamp -> finalize to production-ready)

origin:
  type: onboarded
  source: github.com/msomali/arf-care @ <ARF_SHA from import PR>
  deployment_status: REQUIRED-INPUT        # live at a facility? pilot? never-deployed?
  known_users_or_customers: REQUIRED-INPUT # any facility/staff/family using it today?
  real_data_present: REQUIRED-INPUT        # MUST be "no" in repo/fixtures/dumps before agents touch it.
                                           # Owner certifies as DPC. Synthetic data only.
  credentials_inventory: REQUIRED-INPUT    # list secret NAMES found in old code/.env; rotate on import.
  intent: revamp

target_customer: >
  CA-licensed ARF operators (CCLD) serving regional-center consumers under Title 17;
  users = facility admins, direct-care staff on tablets, family members via portal.

success_metric:
  metric: "ONBOARDED-CONFORMANT (v1 §57.7) + release-candidate deploy passing E2E on core journeys"
  core_journeys: [shift documentation offline->sync, medication administration record entry,
                  incident report creation->review, family portal read access, tenant onboarding]
  baseline: "~80% complete (owner estimate; assessment will reprice)"
  target: RC approved by owner
  horizon: REQUIRED-INPUT (date)

scope:
  - Complete remaining functionality to the parity list PJM extracts from the assessment
  - Test coverage: regression baseline (§57.4) + unit/integration on core journeys
  - Multi-tenant isolation hardening and proof
  - Offline sync conflict semantics documented, implemented, tested
  - Deployment pipeline, backup/restore, rollback target (§57.6)
non_goals:
  - New feature lines beyond parity (billing, analytics, integrations) unless owner re-charters
  - Marketing site, pricing, sales collateral (LIN dormant)

default_tier: T2   # personal-data platform: most tasks trip T2 triggers; first deploy is forced T3 (v2 §82.7)

budget_ceiling:
  money_per_month: REQUIRED-INPUT          # provider credit ceiling is the hard stop (LP-C3)
  note: PJM flags any single task expected to be heavy before dispatching it
timebox: REQUIRED-INPUT
kill_criteria:      # >=3, objective — owner edits
  - assessment shows remaining work > REQUIRED-INPUT weeks at observed pace -> re-charter decision
  - two consecutive weeks with zero merged remediation PRs
  - REQUIRED-INPUT

# ---- ARF Domain Addendum: rows the §57.3 ONB assessment MUST include ----
domain_assessment_addendum:
  security_tenancy:
    - Cross-tenant isolation: automated tests proving no data/object/API access across facilities
    - RBAC matrix: admin / direct-care staff / family (read-only, per-resident scoping) — enforced server-side
    - AuthN/session review incl. tablet shared-device patterns and family portal account lifecycle
  data_protection:
    - PII / health-information inventory (fields, stores, logs) with retention & deletion positions
    - Event store: immutability + correction-by-append policy (no mutation of care records); PII in events reviewed
    - Backup/restore tested; facility offboarding = full data export + verified removal
    - Breach-response note (who is notified, evidence preserved) — owner-approved
  offline_sync:
    - Conflict resolution semantics per event type (last-write? merge? human queue?) documented & tested
    - Idempotent event ingestion; clock-skew handling; retry/duplicate suppression proven
    - Data-at-rest posture on tablets (what persists in the PWA cache; lock/logout behavior)
  compliance_documentation:   # verify rows with a licensing consultant/attorney — not legal advice
    - Incident reporting workflow vs Title 17/22 documentation expectations (SIR-type records)
    - Medication administration record completeness & audit trail
    - Record retention durations per applicable CA requirements
    - HIPAA business-associate exposure assessment for target customers (legal review REQUIRED-INPUT)
  operations:
    - Deployment inventory + rollback target recorded before first redeploy (v1 §57.6)
    - Environment/secret handling: nothing in repo; runtime config documented in SECRETS-MANIFEST names

approval: REQUIRED-INPUT   # owner name + date = charter active
