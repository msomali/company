# OpenClaw AI Software Company Operating Manual

## Version 2.7 — AI Operating System

**Status:** Runtime and operational architecture  
**Primary question answered:** How does the company coordinate agents, context, memory, tools, models, evidence, approvals, and feedback reliably?  
**Dependency:** Requires Version 1.0 Company Foundation  
**Forward compatibility:** Produces the trusted data, traces, evaluations, and governance records required by Version 3.0.  
**Change record:** Appendix D (change history). Parts XVI–XIX bind every requirement to an enforcement mechanism on the OpenClaw stack.

---

## 1. Purpose

Version 2 converts the Version 1 organization from a collection of well-defined roles into a controlled, observable, durable, and evaluable operating system.

It defines:

1. Harness engineering.
2. Context engineering.
3. Loop engineering.
4. Durable workflow and state management.
5. AI agent memory.
6. Knowledge management and retrieval.
7. Tool and Model Context Protocol governance.
8. LLMOps and model/prompt lifecycle.
9. Evaluation systems.
10. Observability and evidence.
11. Identity, permissions, isolation, and security.
12. AI governance and human-in-the-loop controls.
13. Standard operating procedures and automation.
14. Runtime KPIs, SLOs, and incident handling.
15. A staged implementation plan.
16. Enforcement binding of every requirement to the OpenClaw stack (Part XVI).
17. A substrate hardening baseline as a precondition to activation (Part XVII).
18. A compensating-controls register and a testable definition of done with a dry-run acceptance test (Parts XVIII–XIX).

Version 2.1 remains portable in design but is normatively bound to a concrete stack: **hardened OpenClaw (§85) + git/GitHub + model-routing proxy + CI**. Every numbered requirement in this document carries an enforcement class (§77) and a mechanism (§78). A requirement whose mechanism of the declared class does not exist is NOT satisfied — prose alone satisfies nothing except the definition of class-P procedures. Requirements that cannot be hard-enforced on any current stack are formally registered as compensating controls (§86) rather than silently assumed.

# Part I — Operating-System Architecture

## 2. Core Principle: Agent = Model + Harness + Environment

A production agent is not only an LLM prompt. It is a governed system containing:

- An identity and role contract from Version 1.
- A model or model-routing policy.
- A harness.
- Context selection and compression.
- Memory and knowledge access.
- Tools and permissions.
- Workflow state.
- Verification and evaluations.
- Observability.
- Budgets and stop conditions.
- Human oversight.
- An execution environment.
- Versioned artifacts and configuration.

The effectiveness and safety of an agent MUST be evaluated as a complete system, not as a model in isolation.

## 3. Architectural Layers

```text
┌──────────────────────────────────────────────────────────────┐
│ Human Owners, Users, Customers, and External Systems         │
├──────────────────────────────────────────────────────────────┤
│ Intake and Intent Layer                                      │
│ authentication • task classification • risk • project scope  │
├──────────────────────────────────────────────────────────────┤
│ Governance and Policy Control Plane                          │
│ identity • permissions • approvals • budgets • policy-as-code│
├──────────────────────────────────────────────────────────────┤
│ Harness and Workflow Control Plane                           │
│ routing • decomposition • state • loops • retries • gates    │
├──────────────────────────────────────────────────────────────┤
│ Agent Runtime                                                │
│ role contract • model • skills • context • planning • action │
├──────────────────────────────────────────────────────────────┤
│ Context, Memory, and Knowledge Plane                          │
│ task state • project memory • RAG • provenance • retention   │
├──────────────────────────────────────────────────────────────┤
│ Tool and Execution Plane                                     │
│ MCP • APIs • code sandbox • browsers • repositories • CI/CD  │
├──────────────────────────────────────────────────────────────┤
│ Artifact and Evidence Plane                                  │
│ requirements • designs • code • tests • decisions • releases │
├──────────────────────────────────────────────────────────────┤
│ Evals, Observability, and Operations Plane                    │
│ traces • metrics • logs • quality • cost • alerts • incidents│
└──────────────────────────────────────────────────────────────┘
```

## 4. Control Plane vs. Work Plane

### Control Plane

- Agent registry.
- Model, prompt, tool, and policy registries.
- Workflow definitions.
- Permissions and approvals.
- Evaluation thresholds.
- Budgets and quotas.
- Version promotion.
- Audit and change management.

### Work Plane

- Agent executions.
- Tool calls.
- Sandboxed code execution.
- Retrieval.
- Artifact generation.
- Tests and verification.
- Project-specific state.

Agents MUST NOT modify control-plane policy directly. They MAY submit a versioned change proposal for authorized approval.

# Part II — Canonical Runtime Records

## 5. Agent Manifest

Each agent MUST have a machine-readable manifest containing at least:

```yaml
agent_id: SDE
name: Senior Software Development Engineer
agent_version: 1.0.0
role_contract_version: v1.0
owner: human-or-team-id
status: active
model_policy: engineering-default
prompt_bundle_version: sde-prompts-1.0.0
allowed_tools:
  - repository.read
  - repository.write_scoped
  - ci.run
  - test.run
denied_tools:
  - production.deploy
  - customer_data.export
memory_policy: project-engineering
risk_ceiling: high-with-human-approval
required_evals:
  - implementation_correctness
  - security_baseline
  - documentation_completeness
```

## 6. Task Envelope

Every task entering the harness MUST include:

```yaml
task_id: TASK-000123
project_id: PROJECT-001
requested_by: PJM
assigned_role: SAA
objective: >
  Produce an architecture for the approved product requirements.
business_context: ...
inputs:
  - artifact_id: PRD-001
constraints:
  - region: US
risk_class: medium
data_classification: confidential
acceptance_criteria:
  - ...
required_outputs:
  - architecture_spec
priority: high
allowed_tools: inherited-and-narrowed
human_approval_points:
  - architecture_exception
budgets:
  wall_clock_minutes: 120
  model_cost_limit: ...
  tool_call_limit: 100
```

A task lacking objective, acceptance criteria, owner, risk class, and required outputs MUST be rejected or returned for clarification.

## 7. Artifact Manifest

Every artifact MUST record:

- Artifact ID and immutable content hash.
- Project, task, and originating execution.
- Type and format.
- Owner and reviewers.
- Version and status.
- Requirement links.
- Source artifact links.
- Agent, model, prompt, tool, and knowledge versions involved.
- Sensitivity.
- Approval and supersession.
- Creation and modification timestamps.

## 8. Gate Decision Record

Every gate MUST produce:

```yaml
gate_id: GATE-SAT-001
artifact_or_release: RC-2026.07.1
gate_owner: SAT
decision: CHANGES_REQUIRED
criteria_version: quality-gate-2.1
evidence:
  - TEST-RUN-882
findings:
  - DEFECT-431
conditions: []
expires: null
next_owner: SDE
```

## 9. Execution Episode

Every agent run SHOULD produce an auditable episode package:

- Input task envelope.
- Agent, model, prompt, tool, policy, and knowledge versions.
- Context manifest.
- Tool-call trace.
- State transitions.
- Produced artifacts.
- Evaluations and verifier results.
- Cost, tokens, latency, and retries.
- Failures and recovery actions.
- Human interventions.
- Final status and reason.
- Protected or redacted content according to policy.

# Part III — Harness Engineering

## 10. Harness Responsibilities

The harness MUST provide:

1. Task intake and validation.
2. Role and agent selection.
3. Risk and data classification.
4. Context assembly.
5. Tool and permission enforcement.
6. Planning and decomposition.
7. Durable state and checkpoints.
8. Sequential and parallel coordination.
9. Retry, timeout, cancellation, and compensation.
10. Budget enforcement.
11. Verification and gate enforcement.
12. Artifact and provenance tracking.
13. Human approval and override.
14. Observability and audit.
15. Graceful degradation and recovery.
16. Termination conditions.

## 11. Routing

Routing SHOULD consider:

- Required role authority.
- Task type and domain.
- Risk class.
- Data classification.
- Tool requirements.
- Model capability.
- Latency and cost target.
- Agent health and load.
- Separation of duties.
- Prior task history.

Routing MUST NOT assign approval to the same execution that created the artifact when independent review is required.

## 12. Task Decomposition

The harness MAY use deterministic workflows, planner agents, or a hybrid.

Every decomposition MUST:

- Preserve the parent objective.
- Define child acceptance criteria.
- Specify dependencies.
- Assign owners.
- Prevent unauthorized scope expansion.
- Define merge or integration strategy.
- Avoid duplicate work.
- Define stop and escalation conditions.

Parallel work SHOULD be used only when tasks are meaningfully independent or have a conflict-resolution strategy.

## 13. Durable Execution

Long-running work MUST support:

- Checkpointing after material steps.
- Resume after interruption.
- Idempotent steps where practical.
- Duplicate-execution detection.
- Safe retry.
- Explicit state transitions.
- Artifact-based handoff across context windows.
- Recovery without restarting the entire project.
- Timeouts and dead-letter handling.
- Cancellation and cleanup.

## 14. Retry and Recovery Policy

Retries MUST be bounded and distinguish:

- Transient infrastructure failure.
- Rate limit.
- Tool timeout.
- Invalid input.
- Model formatting failure.
- Verification failure.
- Policy denial.
- Repeated reasoning or action loop.

The harness MUST NOT repeatedly retry a deterministic failure without changing conditions. When the retry budget is exhausted, stop, preserve evidence, and escalate.

## 15. Budgets and Circuit Breakers

Each task or workflow MUST support limits for:

- Model cost.
- Token use.
- Tool calls.
- Wall-clock duration.
- Retries.
- Parallel agents.
- Data volume.
- External API use.
- Side-effect operations.

Circuit breakers SHOULD stop execution when:

- Cost or time grows unexpectedly.
- Repeated actions show no progress.
- Security policy is triggered.
- Quality falls below threshold.
- External dependencies fail.
- The agent attempts unauthorized privilege.
- State becomes inconsistent.

## 16. Completion and Stop Conditions

A workflow is complete only when:

- Required artifacts exist.
- Acceptance criteria are verified.
- Required gates pass.
- No blocking finding remains.
- Evidence is stored.
- Next state is unambiguous.

"Looks complete" is not a completion condition.

# Part IV — Context Engineering

## 17. Context as a Managed Resource

Context MUST be selected for relevance, authority, freshness, sensitivity, and token cost.

It includes:

- System and role instructions.
- Task objective and acceptance criteria.
- Current workflow state.
- Relevant artifacts.
- Applicable policies.
- Tool definitions.
- Retrieved knowledge.
- Memory.
- Examples.
- Recent messages and summaries.
- Constraints and budgets.

## 18. Context Precedence

1. Platform and safety policy.
2. Human owner and company constitution.
3. Version 1 role contract and authority.
4. Approved project policy and requirements.
5. Workflow instructions.
6. Task instructions.
7. Retrieved knowledge.
8. User-provided or external untrusted content.

Untrusted content MUST never redefine higher-priority instructions or tool permissions.

## 19. Context Manifest

Record:

- Context item ID.
- Source and owner.
- Version or timestamp.
- Authority level.
- Sensitivity.
- Retrieval reason.
- Relevance where applicable.
- Expiration/freshness.
- Trust classification.
- Whether truncated, summarized, or transformed.

## 20. Context Compression and Compaction

- Preserve goals, decisions, requirements, findings, and unresolved issues.
- Move large intermediate content into artifacts.
- Replace history with verified summaries and links.
- Do not summarize away constraints, risk, or dissent.
- Mark generated summaries and retain sources.
- Revalidate critical state after compaction.
- Use checkpoints before context reset.

## 21. Context Isolation

- Customer, project, and tenant contexts MUST be isolated.
- Sensitive memory MUST NOT enter unrelated tasks.
- Reviewer agents SHOULD receive enough evidence for independent review without unnecessary creator bias.
- External content MUST be labeled untrusted.
- Tool output MUST be sanitized and bounded.

# Part V — Loop Engineering

## 22. Definition

A loop is a repeatable, bounded workflow that observes a state, acts, verifies the result, and decides whether to continue, escalate, roll back, or stop.

Every loop MUST define:

- Objective.
- Entry conditions.
- State.
- Actor.
- Allowed actions.
- Verifier.
- Success and failure criteria.
- Maximum iterations.
- Time and cost budget.
- Escalation.
- Evidence.
- Side-effect and rollback policy.

## 23. Loop Pattern

```text
Observe current state
  → Compare to objective and criteria
  → Select next bounded action
  → Execute in authorized environment
  → Verify with independent or deterministic evidence
  → Record state and evidence
  → Continue, revise, escalate, roll back, or stop
```

## 24. Loop Levels

### 24.1 Micro Loop
Draft → self-check → correct → submit.

### 24.2 Work Loop
Creator → reviewer → findings → creator → verifier.

### 24.3 Stage Loop
Release candidate → gate → remediation → affected regression → recheck.

### 24.4 Product Loop
Customer/market evidence → product decision → delivery → launch → measured outcome.

### 24.5 Operational Loop
Telemetry → detection → diagnosis → mitigation → recovery → post-incident improvement.

### 24.6 AI Improvement Loop
Trace/feedback → evaluation → diagnosis → proposed change → offline eval → controlled release → online monitoring → keep or rollback.

## 25. Anti-Loop Controls

Detect:

- Repeated identical actions.
- Oscillation between states.
- Reviewer/creator deadlock without new evidence.
- Scope expansion.
- Declining quality or increasing cost.
- Self-generated tasks unrelated to objective.
- Repeated retrieval of the same evidence.
- Circular delegation.
- Attempts to lower acceptance criteria.

Stop and escalate with evidence.

## 26. Independent Verification

High-impact loops SHOULD use deterministic tests, independent reviewer agents, different models/prompts where correlated failure is a concern, human review, external evidence, and rollback tests.

The creator model SHOULD NOT be the only judge.

# Part VI — AI Agent Memory

## 27. Memory Architecture

| Layer | Purpose | Typical lifetime |
|---|---|---|
| Execution scratch | Temporary calculations and intermediate state | One step or run |
| Short-term/thread memory | Current conversation or task continuity | Session or thread |
| Working/project memory | Requirements, decisions, bugs, approvals | Project lifecycle |
| Role memory | Approved patterns and role lessons | Long term |
| Organizational memory | Standards, incidents, reusable knowledge | Long term |
| Customer memory | Authorized support/relationship context | Policy-defined |
| Decision memory | Versioned decisions | Long term |
| Episodic memory | Past execution summaries and outcomes | Retention-defined |
| Semantic knowledge | Documents, facts, and definitions | Source lifecycle |

## 28. Memory Record Schema

A memory record MUST include:

- Memory ID.
- Type and namespace.
- Subject and scope.
- Content or artifact link.
- Source and provenance.
- Creator.
- Confidence or verification status.
- Sensitivity and access policy.
- Created, updated, and expiration dates.
- Retention basis.
- Supersession.
- Related entities and decisions.
- Whether user-provided, observed, inferred, or generated.

## 29. Memory Write Policy

Do not write everything to long-term memory. Write only when reusable, relevant, authorized, sufficiently accurate or labeled uncertain, minimally sensitive, retention-defined, and linked to evidence.

High-impact memories SHOULD require verification or approval.

## 30. Memory Read Policy

Apply tenant/project isolation, role access, purpose limitation, sensitivity filtering, freshness, supersession, relevance, source quality, and consent/legal authority.

Memory cannot grant permission or override policy.

## 31. Memory Correction and Forgetting

Support correction, supersession, deletion/legal hold, expiration, user rights, provenance-preserving redaction, tombstones, cache/index purging, and re-indexing.

## 32. Memory Poisoning Defense

Use trusted-source tiers, restricted writes, validation, fact/inference separation, anomaly detection, versioning, audit, quarantine, retrieval filters, and independent verification for high-impact memory.

# Part VII — Knowledge Management and RAG

## 33. Knowledge Lifecycle

```text
Register source
  → classify ownership/trust
  → ingest/parse
  → metadata/sensitivity
  → validate
  → chunk/index
  → evaluate retrieval
  → retrieve with provenance
  → monitor freshness
  → update/deprecate/archive/delete
```

## 34. Source Registry

Record source ID, title, owner, authority tier, scope, version/effective date, sensitivity, jurisdiction/audience, refresh, review/expiry, parser/index version, and supersession.

## 35. Retrieval Requirements

- Approved sources only.
- Permission checks before retrieval.
- Filters by product, tenant, date, authority, and jurisdiction.
- Citations and source IDs preserved.
- Retrieval evaluated separately from answer quality.
- Conflicts detected.
- Current authoritative sources preferred.
- Insufficient evidence stated.
- Unsupported claims avoided.

## 36. Knowledge Quality Metrics

Retrieval precision/recall, citation correctness, freshness, unsupported-claim rate, conflict detection, permission violations, groundedness, and update latency.

# Part VIII — Tool Management and MCP

## 37. Tool Registry

Every tool MUST have ID/version, owner, purpose, schemas, permissions, side-effect class, data accessed, rate/cost limits, timeout/retry, idempotency, audit, security review, tests, and deprecation.

## 38. Side-Effect Classes

| Class | Example | Default control |
|---|---|---|
| Read-only | Search docs, read repository | Logged and permission checked |
| Reversible write | Draft, temporary branch | Scoped; rollback available |
| Material write | Merge code, update record | Explicit authorization |
| External communication | Send email, publish | Human approval or approved policy |
| Financial/legal | Purchase, refund, sign | Human approval mandatory |
| Production/destructive | Deploy, delete, rotate | Strong approval and rollback |
| Code execution | Shell, build | Sandbox and resource restrictions |

## 39. Tool Invocation Security

Tools MUST validate inputs, enforce access, rate limit, sanitize output, use timeouts, log use, minimize data, prevent credential forwarding, mitigate confused-deputy behavior, confirm sensitive actions, and validate results.

Do not load every tool into context when scoped discovery is safer and cheaper.

## 40. MCP Governance

- Register approved servers.
- Verify server identity and authorization.
- Follow current authorization specifications.
- Review tool descriptions as executable contracts.
- Do not treat annotations as security enforcement.
- Prefer enterprise-managed authorization where available.
- Assign owner, scope, trust rating, and incident procedure.
- Isolate local/remote servers according to risk.
- Version and evaluate MCP changes.

## 41. Sandboxed Execution

Use scoped filesystem/network, resource limits, no default production credentials, malware/secret scanning, command/result logging, cleanup, artifact capture, and reproducible environments.

# Part IX — Identity, Permissions, and Trust

## 42. Agent Identity

Every execution MUST have stable agent identity and ephemeral execution identity showing actor, authority, task, project, permissions, tools, credentials, and approvals.

## 43. Least Privilege and Just-in-Time Access

Deny by default; give only required access; use temporary credentials; prohibit sharing; log elevation; revoke when done.

## 44. Inter-Agent Communication

Use structured tasks and artifacts, not unrestricted hidden chat. Include sender, recipient, task, purpose, action, evidence, sensitivity, priority, and status.

An agent cannot delegate authority it does not possess.

# Part X — LLMOps

## 45. Registries

Maintain registries for models/providers, prompts, agents, tools/MCP, skills, datasets/eval sets, embeddings/indexes, guardrails/policies, workflows, and releases.

## 46. Versioning

A deployed AI system is the bundle of:

```text
Agent + role contract + prompts + model/parameters + tools
+ memory policy + knowledge/index + harness/workflow
+ guardrails + evaluation criteria
```

Any material change creates a new version and required eval run.

## 47. Model Routing

Consider task complexity, tool use, context length, structured-output reliability, risk, privacy/residency, latency, cost, evaluation history, and availability.

Fallbacks MUST be evaluated and MUST NOT silently weaken quality or safety.

## 48. Prompt Lifecycle

Prompts require owner, purpose, version, history, tests/evals, dependencies, security review where needed, promotion/rollback, and deprecation.

No direct untracked production prompt editing.

## 49. Release Strategy

Use offline eval, shadow mode, pilot, canary, A/B where ethical, progressive rollout, rollback, and post-release monitoring.

## 50. Cost and Performance

Track tokens, model/tool cost, latency, time to useful result, retries, retrieval/embedding cost, cost by task/project/agent, quality per cost, and budget exceptions.

Caching must respect privacy, freshness, and version.

## 51. AI Supply Chain

Maintain provider/model inventory, terms, data behavior, training/fine-tuning provenance, model cards, AI/SBOM where practical, dependency risk, and exit/fallback.

# Part XI — Evaluation Framework

## 52. Evaluation Philosophy

Evaluate the complete agent system using deterministic checks, code scorers, rubric/reference scoring, LLM judges where appropriate, humans, adversarial tests, and production outcomes.

## 53. Evaluation Levels

1. Component.
2. Agent.
3. Workflow.
4. Product.
5. Organization.

## 54. Evaluation Dimensions

Correctness, completeness, relevance, groundedness, citations, requirement coverage, policy adherence, security, privacy, safety, tool correctness, memory isolation, planning efficiency, stop correctness, robustness, UX, maintainability, latency, cost, and business outcome.

## 55. Evaluation Dataset

Critical capabilities require versioned datasets with normal, edge, negative, historical failure, adversarial, policy-sensitive, tool failure, long-running, escalation, and refusal cases.

Datasets require owners, provenance, sensitivity, and leakage controls.

## 56. Judge Governance

LLM judges require explicit rubrics, human-label calibration, monitoring for bias/drift/position/verbosity/self-preference, versioning, deterministic supplements, minimized biasing context, and recalibration.

## 57. Gate Thresholds

Define mandatory pass/fail, minimum score, non-averagable metrics, sample/confidence requirements, regression tolerance, human review, and rollback triggers.

High averages cannot compensate for critical safety/security/privacy failures.

## 58. Offline and Online Evals

Offline: repeatable pre-release comparison and regression detection.  
Online: lawful sampled traces and outcomes for drift and unknown failures.

Reviewed production failures feed offline datasets.

## 59. Trace-Based Diagnosis

Inspect context, plan, tool choices/arguments/results, memory access, artifacts, retries, errors, verification, and stop reason to attribute failure to model, prompt, context, memory, tool, data, harness, policy, or environment.

# Part XII — Observability and Operations

## 60. Telemetry

Capture request/task IDs, agent/model/prompt/tool/workflow versions, spans, tokens/cost, tool status, retrieval, memory metadata, evals, states, errors/retries, approvals, and outcome.

Sensitive content capture requires explicit protection policy.

## 61. Core Metrics

### Reliability
Task/workflow success, retry/timeout, stuck loops, tool errors, recovery.

### Quality
Eval pass, regressions, unsupported claims, escalation correctness, gate rejection, customer corrections.

### Performance and Cost
Latency, time to useful result, tokens/cost per success, parallelism, cache.

### Safety and Governance
Policy denials, unauthorized attempts, sensitive exposure, memory isolation, overrides, audit completeness.

## 62. SLOs

Critical workflows SHOULD have SLOs for availability, completion, latency, quality, cost, recovery, escalation, and audit completeness.

## 63. Incident Management

AI incidents include harmful output, data exposure, unauthorized action, tool misuse, memory poisoning, prompt injection, regressions, cost runaway, workflow failure, audit loss, and material hallucination.

Process: detect, contain, preserve evidence, rollback, communicate, remediate, review, prevent recurrence.

# Part XIII — AI Governance and Human-in-the-Loop

## 64. Risk Classification

| Class | Description | Oversight |
|---|---|---|
| Low | Informational, reversible, no sensitive data | Automated with monitoring |
| Moderate | Business impact or limited sensitive context | Controls and sampled review |
| High | Material customer, security, privacy, financial, or operational impact | Mandatory approval |
| Prohibited | Unacceptable legal, ethical, safety, or authority risk | Must not execute |

## 65. Human Approval Points

Mandatory for production release until delegated, legal commitments, financial transactions beyond limits, destructive actions, privacy exceptions, security exceptions, employment-like decisions, crisis communication, authority/policy/eval changes, and actions outside competence.

## 66. Human Override

Authorized humans can pause, cancel, revoke, inspect, modify state, approve/reject, rollback, and quarantine agents/models/prompts/tools/memory/knowledge.

All overrides are logged.

## 67. Policy as Code

Enforce tools, data, environments, budgets, approvals, models/providers, memory retention, release gates, region/customer constraints, and prohibited actions.

Decisions must reference rule IDs and evidence.

# Part XIV — Standard Operating Procedures

## 68. New Project Provisioning SOP

1. Create project and owner.
2. Classify data and risk.
3. Load Version 1 roles/workflow.
4. Create artifact, memory, knowledge, telemetry, and permission namespaces.
5. Register sources/tools.
6. Define model policy and budgets.
7. Define gates.
8. Create eval plan/dataset.
9. Define human approvals.
10. Dry run.
11. Review evidence.
12. Activate.

## 69. New Agent or Skill SOP

Need → authority/scope → threat/privacy review → tools/memory → prompt/manifest → eval set → sandbox/shadow → independent review → controlled promotion → monitoring/owner.

## 70. Model or Prompt Change SOP

Proposal → impact → new version → offline eval → security/policy checks → shadow/canary → online monitoring → promote/rollback → document → add failures to evals.

## 71. Tool Onboarding SOP

Owner/purpose → schemas/side effects → auth → privacy/data flow → security → limits/retry/idempotency → sandbox → eval → registry → monitoring/retirement.

## 72. Memory Source Onboarding SOP

Purpose → authority/rights → sensitivity/retention → schema/namespace → validation/poisoning controls → access → correction/deletion → eval → approval → monitoring.

# Part XV — Implementation Roadmap (v2.1)

## 73. Phase 1 — Minimum Enforceable Operating System

**Precondition:** §85 substrate hardening complete, evidence committed.

Implement, in order:

1. Control and artifact repositories per §79 and v1 §52, with branch protection and CODEOWNERS per §80.
2. The GitHub machine identity (§80 as amended by ADR-B000) and the `#approvals` channel per v1 §51.
3. Model access per §81 Mode S (ACTIVE, ADR-B003): human-performed subscription sign-ins on both providers (MODEL-001), named policies mapped in `policies.yaml`, dispatcher token metering against `prices.yaml`, global concurrency cap. Mode P (LiteLLM proxy + API keys) remains fully specified as the dormant fallback; reactivation requires an owner-approved ADR.
4. Agent manifests and the generator producing OpenClaw agent files (§78 row 1; v1 §48.1) for the v1 §50 pilot roster.
5. `task-create` and the dispatcher to the §82 specification, including state.yaml transitions, retry classes, loop caps, and approvals capture.
6. Episode collector (§78 row 5) and the kill-switch/incident SOP (row 28).
7. Memory tree with PR-gated writes (§83).
8. Tool registry, generated allowlists, vendored skills, per-agent sandboxes (§78 rows 16–18).
9. Deterministic eval CI per §84 with initial golden tasks for PJM, SDE, SAT, DCE.
10. Weekly metrics script (§78 row 26).
11. The §88 dry run, passed in full.

**Explicit Phase 1 exclusions** (deferred, not skipped): vector retrieval, LLM-judge evals, shadow/canary releases, OTel GenAI telemetry, OPA-class policy engine, JIT credentials, Temporal-class workflow engine, autonomous self-improvement.

## 74. Phase 2 — Durable Harness and Loops

Add: retrieval service with provenance and permission filters (§78 row 15) and activation of §35–36; rubric and LLM-judge evaluation under §56 governance (row 24); shadow and canary release for prompt bundles (row 21); context-manifest automation and compaction checkpointing (row 10); loop analytics on episode data; online eval sampling of production traces (§58); parallel sub-agent workstreams with conflict-resolution strategy (§12); incident-process drills against real workloads.

**Phase 2 entry:** Phase 1 complete per §87 plus at least one real project shipped through all gates.

## 75. Phase 3 — Mature LLMOps and Governance

Add: OTel GenAI semantic-convention telemetry and dashboards (rows 5, 26); OPA-class policy engine replacing policy set v0 (row 30); JIT, expiring credentials (§43); automated model routing and evaluated fallbacks (§47); SLOs per §62 from Phase 1–2 baselines; red-team eval suites (§55 adversarial classes); memory lifecycle automation (§31); Temporal-class durable execution **only if** state.yaml durability has demonstrably failed under load (row 7 condition).

**Phase 3 entry:** Phase 2 complete plus stable weekly metrics for one quarter.

## 76. Version 2.1 Exit Criteria

- Every material execution produces a complete episode package (§9, row 5).
- All agent, model, prompt, tool, policy, and knowledge versions are traceable to control-repo tags (§78 row 20).
- Core workflows resume from state.yaml after interruption without restarting the project (row 7), demonstrated in the dry run and once in production.
- Gates are structurally enforced: no merge without the owning gate identity's review; separation of duties demonstrated per §88 check 6.
- Evals run before every promotion of prompts, manifests, or policies, and sampled production failures feed the eval sets (§58, §84).
- Permissions are least-privilege, per-agent, and auditable (rows 16–19); the §86 register is current and human-approved.
- Memory and knowledge enforce isolation, provenance, PR-gated writes, retention, and deletion (§83).
- Human override, kill switch, and rollback are installed and drilled (§88 checks 12–13).
- Quality, cost, latency, gate-rejection, and incident metrics are produced weekly (row 26).
- §87 Definition of Done evaluates true for the declared phase, and at least two projects have produced trustworthy outcome history before Version 3 provisioning begins.

# Part XVI — Enforcement Binding (Normative, v2.1)

Part XVI binds every Version 2 requirement to a concrete enforcement mechanism on the OpenClaw stack: **OpenClaw (hardened per §85) + git/GitHub + model-routing proxy + CI**. A requirement is satisfied only when its mechanism of the declared class exists and has been exercised (§88). Prose satisfies nothing except the definition of class-P procedures.

## 77. Enforcement Classes

| Class | Meaning | Satisfied when |
|---|---|---|
| **N** | OpenClaw-native configuration | Config exists in the control repo and is loaded by the gateway |
| **G** | Git/GitHub-enforced | Branch protection, CODEOWNERS, required reviews/checks active and demonstrated |
| **S** | Script or middleware built by the company | Code merged in the control repo, tested, exercised in the dry run |
| **P** | Human procedure | Written SOP in `/control/sops/` plus evidence of execution in the dry run |
| **C** | Compensating control only | Cannot be hard-enforced; register entry in §86 approved by the human owner |
| **X** | External managed service | Account configured; configuration versioned in the control repo |

Rules: every normative statement in this document inherits the class of its subsystem row in §78 unless individually tagged. Class-C items MUST appear in the §86 register. Changing a class is change management (v1 §44).

## 78. Binding Map (Normative)

| # | Subsystem (refs) | Mechanism | Class | Phase |
|---|---|---|---|---|
| 1 | Agent manifests (§5) | YAML manifests in `/control/manifests/`; generator emits OpenClaw agent config + TOOLS.md per v1 §48.1; CI validates schema. Fields OpenClaw cannot consume (`risk_ceiling`, `required_evals`) are consumed by CI and the dispatcher | S | 1 |
| 2 | Task envelope (§6) | `task-create` CLI validates against a JSON Schema, writes `/projects/*/episodes/TASK-###/task.yaml`, dispatches via `sessions_spawn`. Invalid envelopes are rejected before any model call | S | 1 |
| 3 | Artifact manifest (§7) | YAML front matter (v1 §52.3) + commit SHA as content hash; CI lints completeness and ID uniqueness on every PR | G | 1 |
| 4 | Gate decision records (§8) | Single machine identity `agenticfoundrybot` authors; the human owner is the required reviewer (§80 as amended by ADR-B000). CODEOWNERS + required reviews make self-approval structurally impossible; per-gate role attribution is carried in the handoff template and gate record (§86-C6). A merge hook writes `gates/GATE-*.yaml` | G | 1 |
| 5 | Execution episode (§9) | Collector script bundles task.yaml, state.yaml, session transcript export, PR references, CI run links, and proxy cost lines into `episodes/TASK-###/`. Full OTel GenAI telemetry deferred | S | 1 (OTel: 3) |
| 6 | Routing (§11), decomposition (§12) | Deterministic dispatcher (task-type → role → agent table). Planner agents may propose child tasks; proposals re-enter `task-create` validation. Separation of duties checked at dispatch | S | 1 |
| 7 | Durable execution (§13) | Durability via git, not a workflow engine: `state.yaml` per task implements the Appendix A state machine; every transition is a commit; resume = re-dispatch from state.yaml; task IDs are idempotency keys; dead-letter = BLOCKED state + escalation record. Temporal is adopted only if dry-run/production evidence shows this insufficient | S | 1 (Temporal: 3, conditional) |
| 8 | Retry policy (§14), budgets/breakers (§15) | Dispatcher implements the retry-class table (§82) with caps. Budgets per §81 active mode — Mode S: provider credit ceiling + dispatcher token metering against `prices.yaml`; Mode P: proxy virtual keys and caps. Circuit breaker = pause script: halt dispatch, stop sessions/containers (Mode P additionally revokes the key), set BLOCKED | S | 1 |
| 9 | Context precedence (§18) | Digest embedded in AGENTS.md; fetch/tool wrappers label external content UNTRUSTED. Hard in-model enforcement is impossible → register entry C1. Backstops: tool absence, side-effect gates, independent review | N+C | 1 |
| 10 | Context manifest (§19), compaction (§20) | Episode collector records context inputs per dispatch; compaction rules live in AGENTS.md; checkpoints = commits before compaction | S+P | 2 |
| 11 | Context isolation (§21) | Per-project OpenClaw workspaces; per-agent memory directories; no shared sessions for creation and review of the same artifact (v1 §48.4) | N | 1 |
| 12 | Loop engineering (§22–25) | Dispatcher enforces iteration caps and an oscillation counter (identical-action detection; rejection-cycle count per v1 §54). Exceeding caps → BLOCKED + escalation | S | 1 |
| 13 | Independent verification (§26) | SAT runs on a different model family than the implementer (proxy policy, v1 §48.3) plus deterministic CI tests as the non-model verifier | N+G | 1 |
| 14 | Memory (§27–32) | `/memory/` tree with §28 front matter. Writes to role/organizational memory occur **only via reviewed PR** — this single rule implements §29 write policy and the core of §32 poisoning defense. Project memory = workspace files. Deletion = PR + index-purge script + tombstone | G+S | 1 |
| 15 | Knowledge/RAG (§33–36) | Phase 1: no vector store. `SOURCES.yaml` registry + curated repo docs + file search; citations = repo paths. Phase 2: retrieval service (X) with provenance and permission filters; §36 metrics activate then | P → X | 1 → 2 |
| 16 | Tool registry (§37), side-effect classes (§38), invocation security (§39) | `TOOLS.yaml` registry generates per-agent allowlists; OpenClaw deny-wins layering means each level only restricts further. Mapping: external-communication and production tools are **absent** from all TOOLS.md except DCE's deploy path; material writes require the G-class gate; code execution only in sandboxes (row 18) | N+G | 1 |
| 17 | MCP governance (§40) | MCP servers and skills are registry entries in `TOOLS.yaml` with owner, scope, trust tier. **Zero direct marketplace installs:** every skill is vendored into `/control/skills/` after the source-review checklist (§85.5) and pinned by hash | P+G | 1 |
| 18 | Sandboxed execution (§41) | Per-agent containers with scoped mounts, no production credentials by default, egress allowlist, resource limits, cleanup | S | 1 |
| 19 | Identity and permissions (§42–44) | Per-agent proxy keys; per-agent containers and env vars; GitHub authorship via the single machine identity with mandatory human review (ADR-B000, §86-C6). Inter-agent communication of record = task envelopes + PRs (v1 §53); an agent cannot delegate authority its TOOLS.md does not contain | S+G | 1 |
| 20 | LLMOps registries (§45–48) | Registries = versioned directories in `/control/` (models, prompts, tools, workflows, datasets). A release = a git tag of the control repo. Prompt changes = PR + eval CI (row 24). No untracked production prompt edits is enforced by generated-file rule (v1 §48.1) | G | 1 |
| 21 | Release strategy (§49) | Phase 1: offline eval + human release only. Shadow and canary for prompt bundles activate in Phase 2 | G → S | 1 → 2 |
| 22 | Cost and performance (§50) | Mode S: dispatcher-metered tokens per agent/task/project priced via `prices.yaml` (estimated cost); Mode P: proxy usage export (billed cost). Weekly report script commits a metrics artifact either way | S | 1 |
| 23 | AI supply chain (§51) | `PROVIDERS.yaml` inventory + provider/skill/dependency review SOP | P | 1 |
| 24 | Evaluation framework (§52–58) | Phase 1: deterministic evals only — golden tasks per active agent scored by code, plus product unit/integration tests; CI blocks any PR touching `/control/prompts|manifests|policies` on regression. Phase 2: rubric and LLM-judge evals under §56 governance | S+G | 1 → 2 |
| 25 | Trace-based diagnosis (§59) | Episode packages + transcripts are the Phase 1 diagnostic surface | S | 1 |
| 26 | Telemetry (§60–61) | Phase 1: transcripts + CI logs + proxy usage; weekly metrics script computes success, gate-rejection, cost, latency. OTel GenAI semantic conventions in Phase 3 | S | 1 → 3 |
| 27 | SLOs (§62) | Deferred to Phase 3 (requires Phase 1–2 baselines) | — | 3 |
| 28 | Incident management (§63) | `INCIDENT.md` SOP + kill-switch script: stop containers/sessions, revoke model access (Mode P: proxy keys; Mode S: deactivate OAuth auth profiles / stop the gateway), freeze protected branches, preserve episode evidence | P+S | 1 |
| 29 | Risk classification & HITL (§64–66) | Risk class and tier are mandatory envelope fields (validator-enforced). Human approvals = required review on protected branches + `APPROVE` message in `#approvals` captured into the gate record (v1 §51). Override = kill switch + state edit via PR | G+P+S | 1 |
| 30 | Policy as code (§67) | Phase 1 policy set v0 = branch protection + CODEOWNERS + dispatcher checks + proxy budget rules, each with a rule ID referenced in gate records. OPA-class engine in Phase 3 | G+S → X | 1 → 3 |
| 31 | SOPs (§68–72) | Checklists in `/control/sops/`. The §68 New Project Provisioning dry run is formalized as the §88 completion test | P | 1 |
| 32 | Existing project onboarding (v1 §57) | Onboarding charter with origin block; `BASELINE` import PR gated by POL-009; `ONB-###` assessment from `/control/templates/onboarding-assessment.md`; remediation as standard envelopes; dispatcher forces T3 on the first DEPLOYMENT-state task of any `origin: onboarded` project | G+P+S | 1 |

## 79. Control Repository Standard

```text
/control/
  manifests/        agent manifests (§5) — source of generated agent files
  prompts/          versioned prompt bundles per agent
  tools/            TOOLS.yaml registry; generated allowlists; vendored skills/
  models/           policies.yaml (reasoning-max | standard | economy), providers
  policies/         policy set v0 with rule IDs
  evals/<agent>/    golden-task cases + runner config
  sops/             provisioning, incident, hardening, review checklists
  schemas/          task envelope, front matter, gate record JSON Schemas
```

Protected branches: `main` requires PR + required checks + review by the owning gate identity; `gates/` and `episodes/` paths are writable only by CI. Direct pushes to protected branches are disabled for all identities including the human owner.

## 80. GitHub Identity and Branch Protection Standard

*(as amended by ADR-B000 — single machine identity — and ADR-B002 — token placement, as amended 2026-07-17)*

1. Machine identity: one account, `agenticfoundrybot`, authors all agent commits and PRs (active and on-demand roles alike). The human owner's account is the reviewer/merger. HUMAN-HELD gates (SSE, DPC in v1.1) use the human's review directly. The three-identity design (`sat-bot`, `dce-bot`, `pjm-bot`) is preserved as the documented upgrade path in ADR-B000: create the accounts, split CODEOWNERS, no other structural change.
2. CODEOWNERS maps every gated path to the human owner (e.g., `/projects/**/releases/ @agenticfoundrybot @<human>`, `/control/** @<human>`), so no bot-authored PR can merge without human review.
3. Required-review settings prohibit approval by an identity that authored commits on the PR — the structural implementation of v1 §8 separation of duties. Under ADR-B000 this means `agenticfoundrybot` can never approve its own PRs; only the human can. Per-gate role attribution (which role reviewed what) is carried in the handoff template and the emitted gate record and is verified by the human at merge (§86-C6).
4. Token custody: the dispatcher's own tokens (approvals-channel token, proxy admin key) live only in the dispatcher's environment, never in agent contexts. The bot PAT is the one registered exception (ADR-B002, §86-C7): a **classic** PAT with `repo` + `workflow` scopes and 90-day expiry, stored as a GitHub Actions secret **and** as a workspace-local gitignored file (mode 600) readable by agents for git/gh auth; rotation updates both homes in the same sitting or CI breaks silently (gate-writer depends on the secret copy); revoked at B8.1 and on any incident. Fine-grained tokens are structurally unavailable here (established 2026-07-16): GitHub fine-grained PATs cannot access repositories their owner does not own, and `agenticfoundrybot` is a collaborator on the company repo, not its owner. `workflow` scope is required because the repository contains Actions workflow files that agents author and modify (B1.3, B5.2). The breadth of `repo` scope is bounded by account hygiene, not by the token: `agenticfoundrybot` MUST remain a collaborator on this repository only. The least-privilege design (fine-grained, Contents + Pull requests RW) becomes available if the repository moves to an organization — org-owned repos accept fine-grained tokens with per-repo selection; adopting it is then a config migration, not a redesign.
5. Infrastructure identity (ADR-B002 as amended; owner rider to the B4.3 install, 2026-07-17): the dispatcher is not an agent and does not hold the bot PAT. It authenticates with its own repository deploy key (ed25519, read-write, host-side under the `dispatcher` OS user, mode 600) and authors state/episode commits as `dispatcher <dispatcher@company.local>`. This keeps the provenance ledger three-way — owner / agent-roles / infrastructure — and makes the dispatcher independently revocable: the kill switch severs its push access without touching agent identity (§78 row 28). The dispatcher never pushes to `main`; state and episode artifacts reach `main` only via `dispatch/TASK-###` branches and the ordinary PR path.

## 81. Model Access and Budget Standard (dual-mode, v2.3)

The active mode is declared in `/control/models/policies.yaml`. Switching modes is an ADR + §44 change, not a silent edit.

**Mode S — Subscription/account auth (ACTIVE, ADR-B003).**
1. Each agent authenticates via its own OpenClaw auth store (`~/.openclaw/agents/<agentId>/`). agentDirs are never reused or copied between agents; OAuth refresh tokens are not cloned into secondary stores.
2. Provider-side budget reality (as of 2026-07-14): the plan's usage limits are the ceiling — Anthropic's announced Agent SDK credit split (2026-05-13) was paused on 2026-06-15 with subscription limits unchanged and a revision pending under an advance-notice commitment. If the split returns, the per-user monthly credit plus the opt-in overflow dollar cap becomes the hard account budget. Either way the pool is shared by all agents with no per-agent provider caps (registered as §86-C5); the dispatcher metering in item 3 is the budget mechanism of record.
3. Per-task budgeting is dispatcher-enforced: token usage from every model response is recorded into the episode package and priced against `/control/models/prices.yaml` (human-maintained). Envelope `model_budget_tag` maps to an estimated-cost ceiling; breach → task BLOCKED.
4. Global concurrency cap on simultaneous model sessions (default 3, config in policies.yaml) — all agents share one account's rate limits.
5. Named policies (`reasoning-max`, `standard`, `economy`) map to provider/model per account. Decorrelation rule unchanged: SAT resolves to a different model family/provider than the implementer of the same artifact — with one Anthropic and one OpenAI account this is a routing rule, not extra cost.
6. Custody: sign-in is a human act. OAuth tokens live only in agent auth stores, never in the repo, never in agent context, never in SECRETS-MANIFEST destinations.

**Mode P — Routing proxy (DORMANT fallback — reactivation requires an owner-approved ADR; ADR-B003).**
The standard in force: LiteLLM-class proxy in Docker, per-agent virtual keys, per-task budget tags, hard monthly caps with 60%/85% alerts, key suspension as the breaker, provider keys only in the proxy env.

**Both modes:** model traffic configuration is versioned in `/control/models/`; changes to policies, prices, or mode are PRs subject to eval CI.

## 82. Dispatcher and `task-create` Behavioral Specification

The dispatcher and `task-create` are Phase 1 build items. This section is their acceptance specification.

1. **task-create**: validates the envelope against `/control/schemas/task.json` (objective, acceptance criteria, owner role, risk class, tier, required outputs, budgets are mandatory); allocates TASK-###; writes task.yaml + initial state.yaml (`INTAKE`); returns the ID. Invalid input → rejection with the failing fields; no model call occurs.
2. **Dispatch**: resolves role → agent via the §78 row-6 table; verifies separation of duties (creator ≠ required reviewer identity); injects digest reference, envelope, and artifact links into the sub-agent prompt (v1 §48.2); spawns via `sessions_spawn`; records the run ID in state.yaml.
3. **Retry classes and defaults**: transient infra / rate limit → retry ≤ 2 with backoff; tool timeout → retry 1; invalid input / policy denial / verification failure → no retry, return to owner; format failure → 1 reformat attempt; loop detection (identical action ×3, or rejection cycles ≥ 2) → BLOCKED + ESC record. Wall-clock caps per tier: T1 30 min, T2 120 min, T3 explicit in envelope. Tool-call caps: T1 25, T2 100, T3 explicit.
4. **State transitions**: only the dispatcher and CI write state.yaml; every transition is a commit referencing evidence.
5. **Approvals capture**: watches `#approvals`; on `APPROVE/REJECT <task-id> <gate>`, writes the gate record fields and transitions state.
6. **Logs**: every action appends to the episode package.
7. **Onboarded-project rule** (v1 §57.6): for projects whose charter carries `origin.type: onboarded`, the dispatcher forces tier T3 on the first task reaching the DEPLOYMENT state, regardless of the envelope tier.
8. **Metering and concurrency** (§81 Mode S): record model/token usage from every call into the episode package; compute estimated cost from `/control/models/prices.yaml`; enforce the envelope cost ceiling and the global concurrent-session cap; queue dispatches above the cap rather than failing them.

## 83. Memory Binding

1. Write path: role and organizational memory records enter `/memory/**` only through a PR reviewed by the namespace owner (CODEOWNERS). Project working memory is ordinary workspace files.
2. Records carry §28 front matter; `type: user_provided | observed | inferred | generated` is mandatory.
3. Read path: retrieval is by path/glob within the agent's namespace; sensitivity is enforced by directory-level CODEOWNERS and repo permissions.
4. Forgetting: deletion PR + tombstone front matter + purge script for any derived index; supersession per v1 §52.4.

## 84. Evaluation CI Standard (Phase 1)

1. `/control/evals/<agent>/` holds golden-task cases: input envelope + deterministic checks (required artifacts exist, front matter valid, tests pass, forbidden patterns absent, budget respected).
2. The eval runner executes on every PR touching `/control/prompts/**`, `/control/manifests/**`, or `/control/policies/**`, and nightly.
3. Blocking: any regression on a mandatory check fails the required status; high averages cannot offset a failed mandatory check (§57).
4. Every dry-run or production failure that reaches a gate is converted into a new case (§58).
5. Judge-based scoring slots are reserved but disabled until Phase 2 (§56 governance prerequisites).

# Part XVII — Substrate Hardening Baseline (Normative Precondition, v2.1)

## 85. Hardening Requirements

No Phase 1 activation may occur before every item below is completed and the evidence checklist is committed to `/control/sops/hardening-evidence.md`.

1. **Version floor.** The deployed OpenClaw version MUST be the latest stable release at provisioning time, and in no case may it lack the official fixes for CVE-2026-25253 and CVE-2026-32922 — these are minimum floor markers, not the current bar; the project's 2026 advisory cadence has run far past them. Record the exact version and date in the evidence checklist; the weekly advisory-review SOP is in force thereafter.
2. **Authentication.** Gateway authentication enabled; no default, empty, or shared tokens; Control UI access requires auth.
3. **Network.** Gateway bound to loopback; remote access only via Tailscale or SSH tunnel; no public exposure of the gateway port; exposure verified from outside the host and re-checked monthly.
4. **Execution isolation.** All agent code execution occurs in per-agent containers with scoped mounts, read-only roots where practical, resource limits, and an egress allowlist. For artifacts touching credentials or customer data, a fail-closed hardened runtime variant is used.
5. **Skills.** Zero direct marketplace installs. Every skill is vendored into `/control/skills/` after a source review covering: external payload URLs, prerequisite blocks that instruct terminal actions, encoded strings, download-and-execute patterns, and oversized padding; then pinned by hash.
6. **Credentials.** Mode S: provider sign-in is performed by the human into each agent's own auth store; agentDirs are never reused, and tokens never enter the repo, prompts, or agent context. Mode P: provider API keys exist only in the proxy environment. In both modes: no browser-profile, password-manager, or broad OAuth grants to agents; production credentials exist only inside DCE's human-gated deploy path.
7. **High-privilege plugins.** Browser automation and host-level execution plugins disabled except where a specific task tier requires them, and then only inside the sandbox.
8. **Host.** Dedicated VM or user account; default-deny inbound firewall; patched OS; off-host backup of the control and artifact repositories.
9. **Kill switch.** The §78 row-28 script is installed and drilled before activation.

# Part XVIII — Compensating Controls Register (Normative, v2.1)

## 86. Register

Class-C requirements cannot be hard-enforced by any current mechanism on this stack. Each entry below MUST carry human-owner approval and a quarterly review date. Pretending these are enforced elsewhere is prohibited.

**C1 — In-model context precedence (§18).** *Why unenforceable:* instruction priority inside a language model cannot be guaranteed against adversarial content. *Mitigations:* digest primacy in AGENTS.md; UNTRUSTED labeling of external content; tools absent rather than forbidden; every side-effect ≥ reversible-write behind a G-class gate; independent review on different model family. *Residual risk:* instruction-following failure during read-only work products. *Backstop:* nothing material merges or executes without an independent gate. *Owner:* SSE (human-held).

**C2 — Mid-generation budget interruption (§15).** *Why:* caps apply between steps, not mid-token. *Mitigations:* small bounded steps; per-call max-token limits; proxy hard caps; breaker between iterations. *Residual risk:* single-call overrun bounded by max-token setting. *Owner:* DCE.

**C3 — Cryptographically attested per-execution identity (§42).** *Why:* the substrate provides no attestation. *Mitigations:* per-agent keys, containers, and GitHub identities; episode packages tie actions to identities. *Residual risk:* host-level compromise conflates identities. *Backstop:* §85 hardening + incident SOP + kill switch. *Owner:* SSE (human-held).

**C4 — Prompt-injection immunity (§39, §32).** *Why:* not achievable with current models. *Mitigations:* C1 set; vendored skills only; no unreviewed retrieval sources in Phase 1; memory writes via reviewed PR. *Residual risk:* novel injection during browsing/tool use. *Backstop:* human release gate on all production and external actions; kill switch. *Owner:* SSE (human-held).

**C5 — Shared provider identity and subscription-policy volatility (§81 Mode S).** *Why unenforceable:* account auth gives all agents one provider identity, one shared credit pool, and shared rate limits; per-agent provider-side caps do not exist, and provider policy for third-party harness use moved four times in five months of 2026: early restrictions (February), a hard block (April 4), a metered Agent SDK credit plan (announced May 13, effective June 15), and a pause of that plan (June 15) leaving subscription limits unchanged with a revision pending under an advance-notice commitment. OpenClaw's own documentation records the usage as provider-sanctioned "unless Anthropic publishes a new policy" while still recommending API keys as the safer production path — which is exactly what the dormant Mode P preserves. *Mitigations:* provider credit ceiling as the hard account budget; dispatcher token metering + per-task cost ceilings; global concurrency cap; per-agent auth stores never shared; dual-mode §81 so a policy swing is a config migration, not a redesign. *Residual risk:* one agent's runaway usage starves or drains the pool; provider policy changes on short notice. *Backstop:* breaker halts dispatch; human owns provider relationship and plan tier. *Owner:* human owner. *Review:* quarterly and on any provider terms change. *Status:* ACTIVE while Mode S is the declared mode (ADR-B003).

**C6 — Per-gate identity separation within bot output (ADR-B000).** *Why unenforceable:* one machine account posts for every role, so GitHub cannot structurally distinguish which role authored or reviewed an artifact. *Mitigations:* handoff template states role and gate explicitly; gate records carry the claimed role; the human owner reviews gate attribution at merge, not just code correctness. *Residual risk:* a mis-attributed gate (bot claims SAT reviewed what was SDE output) is caught only by human read. *Backstop:* the human is the sole merger on all gated paths. *Owner:* human owner. *Review:* revisit when review volume exceeds careful single-person attribution; upgrade path = per-gate identities per ADR-B000.

**C7 — Bot PAT resident in agent-readable workspace (ADR-B002).** *Why unenforceable:* OpenClaw blocks bind-mounting system paths (`/etc/*`, credential stores, docker.sock) into sandbox containers, and agents must authenticate `git push`/`gh` from inside the sandbox — the only mountable location is the workspace tree, which is agent-readable space. A second, compounding constraint (established 2026-07-16): GitHub fine-grained PATs cannot reach repositories their owner does not own, so a collaborator machine account cannot hold a least-privilege token at all — the live credential is a classic PAT with `repo` + `workflow` scopes (§80.4). *Mitigations:* the bot account is a collaborator on exactly one repository, which is what bounds `repo` scope — `agenticfoundrybot` MUST NOT be added to any other repository; `.secrets/` gitignored before the file exists; file mode 600; gitleaks CI (POL-009) on every PR; 90-day rotation updating both homes (workspace file + Actions secret) in one sitting; agents read it only into `GH_TOKEN` for git/gh invocation and never print, echo, log, commit, or transmit it (BA-2 as amended). *Residual risk:* a prompt-injected or malfunctioning agent exfiltrates the token; the attacker gains write to this repository's branches until revocation. `workflow` scope additionally permits pushing a modified Actions workflow on a branch, which then executes with the repository's Actions secrets — currently bounded, because the only Actions secret is the bot's own PAT; a second Actions secret widens this and triggers a C7 review. Protected branches and required human review still block any merge to `main`. *Backstop:* branch protection + human-only merge; kill switch revokes the PAT; incident SOP. *Owner:* human owner. *Review:* quarterly; on the addition of any second Actions secret; whenever a host-side credential-broker mechanism becomes available in OpenClaw; and immediately if the repository moves to an organization, which makes fine-grained least-privilege available (§80.4).

# Part XIX — Completion Definition and Dry Run (v2.1)

## 87. Definition of Done

**Version 2.1 Phase 1 is complete if and only if:** (a) the §85 evidence checklist is committed; (b) every Phase-1 row in §78 has its mechanism merged, configured, and referenced from the control repo; (c) the §86 register carries human-owner approval; (d) the §88 dry run passes in full; (e) a first weekly metrics artifact (row 26) has been generated. Phases 2 and 3 are complete when their §78 rows meet the same standard. No prose, intention, or partial script counts.

## 88. Dry-Run Acceptance Test

Executed on synthetic `PROJECT-000` with an approved charter (v1 §56). All fourteen checks must pass; any failure means Phase 1 is not complete.

1. `task-create` accepts a valid T2 envelope and writes task.yaml + state.yaml.
2. `task-create` rejects an envelope missing acceptance criteria **before any model call**.
3. Dispatcher spawns SDE with digest reference, envelope, and artifact links present in the sub-agent prompt.
4. SDE opens a PR using the handoff template; CI blocks it while a front-matter field is missing, passes once fixed.
5. A SAT gate review — posted by `agenticfoundrybot` under explicit SAT attribution in the gate-record format (§86-C6) — requests changes (cycle 1); SDE revises; SAT posts an approval recommendation; the human owner's required review confirms it (cycle 2 closed without escalation).
6. A GitHub approval attempted from `agenticfoundrybot` on its own PR is rejected (author-review block), and a merge attempted without the human owner's review is blocked by required reviews (separation of duties demonstrated).
7. Merge emits `gates/GATE-SAT-*.yaml` with evidence links.
8. SSE/DPC human-held approvals are issued in `#approvals` and captured into gate records by the dispatcher.
9. A merge attempted to the release branch without the human `APPROVE` is blocked; with it, it succeeds.
10. The episode package for the task is assembled and passes the §9 completeness checklist.
11. The cost report shows the task with per-agent usage: metered tokens and estimated cost (Mode S) or proxy-billed spend (Mode P).
12. Breaker test: a task with a 1-tool-call budget halts BLOCKED with evidence, without retry-looping.
13. Kill-switch drill: pause stops sessions/containers and revokes model access (proxy keys in Mode P; OAuth-profile deactivation/gateway stop in Mode S); resume re-dispatches from state.yaml and completes.
14. A synthetic prompt-bundle PR with a failing golden task is blocked by eval CI; after fixing, it merges and is tagged as a release.

Record the run itself as an episode. Convert every friction point discovered into either a §78 mechanism fix or a new eval case before declaring completion.

# Appendix A — Reference Workflow State Machine

```text
INTAKE
  → DISCOVERY
  → REQUIREMENTS
  → DESIGN
  → DELIVERY_PLAN
  → IMPLEMENTATION
  → QUALITY_REVIEW ↺ REMEDIATION
  → SECURITY_REVIEW ↺ REMEDIATION + REGRESSION
  → PRIVACY_COMPLIANCE_REVIEW ↺ REMEDIATION + REGRESSION
  → PRODUCTION_READINESS
  → PRODUCT_ACCEPTANCE
  → HUMAN_RELEASE_AUTHORIZATION
  → DEPLOYMENT
  → PRODUCTION_VERIFICATION
  → OPERATIONS_AND_FEEDBACK
  → CLOSED / ITERATION / INCIDENT
```

# Appendix B — Standards and Evidence Base

Maintain alignment with current official guidance including:

- Anthropic guidance on effective agents, context engineering, long-running harnesses, tool design, multi-agent systems, and evals.
- NIST AI Risk Management Framework and Generative AI Profile.
- OWASP LLM, agentic application, prompt-injection, and AI-agent security guidance.
- Model Context Protocol specification, authorization, tools, and security guidance.
- OpenTelemetry GenAI traces, metrics, and events.
- Mature LLM/agent evaluation, LLMOps, MLOps, SRE, DevSecOps, privacy, and supply-chain practices.

# Appendix C — Version 2 Design Principles

1. Prefer simple workflows before autonomy.
2. Make state explicit.
3. Put durable context in artifacts.
4. Make side effects attributable and reversible.
5. Verify with evidence.
6. Bound loops.
7. Deny permissions by default.
8. Treat memory and tools as attack surfaces.
9. Evaluate the complete system.
10. Preserve human authority.
11. Optimize quality, latency, and cost together.
12. Turn repeated failures into harness improvements.

---

# Appendix D — Change Record (v2.0 → v2.1)

Per v1 §44 change management.

**Problem.** v2.0 declared itself platform-neutral and deferred all implementation, leaving "complete" untestable: no mapping from requirement to mechanism, no statement of what OpenClaw provides natively versus what must be built, no substrate security baseline despite the platform's documented incident history, no honest register of requirements that cannot be hard-enforced, and exit criteria that could never evaluate true or false.

**Changes.**

1. §1 rewritten: platform-neutrality replaced by normative binding to the hardened OpenClaw + git/GitHub + proxy + CI stack; scope items 16–18 added.
2. Part XVI added (§77–84): enforcement classes; the normative binding map covering every v2 subsystem; control-repository, GitHub-identity, model-routing/budget, dispatcher, memory-binding, and eval-CI standards.
3. Part XVII added (§85): substrate hardening baseline as a hard precondition to Phase 1.
4. Part XVIII added (§86): compensating-controls register (C1–C4) with mitigations, residual risk, backstops, and owners.
5. Part XIX added (§87–88): testable definition of done and a fourteen-check dry-run acceptance test, formalizing the §68 SOP dry run.
6. Part XV (§73–76) rewritten: phases now list concrete mechanisms with explicit exclusions and entry conditions; exit criteria reference §87/§88 and are individually verifiable.

**Affected.** All agents (generated files, proxy keys, sandboxes); all workflows (dispatcher, state.yaml, PR transport per v1 §53); the human owner (§85 evidence, §86 approvals, §88 execution).

**Compatibility.** Extends v2.0. No behavior or evidence requirement is weakened. Requirements re-scoped to Phase 2/3 remain mandatory at those phases and are explicitly listed as exclusions, not silently dropped. Class-C entries convert previously implicit gaps into governed, reviewed controls — a strengthening of auditability.

**Migration.** Execute §85; build Phase 1 items 1–10 in the §73 order; pass §88; then declare Phase 1 complete per §87.

**Approvals.** Human owner — pending signature.

**Version.** 2.1. v2.0 is preserved unmodified as the prior version.

---

## v2.1 → v2.2

**Problem.** v1 §57 (onboarding) had no enforcement mechanism.
**Changes.** §78 row 32 added; §82 item 7 added (dispatcher-forced T3 first redeploy for onboarded projects); onboarding-assessment template added to the seed kit.
**Compatibility.** Extends v2.1; nothing weakened. **Version.** 2.2. v2.1 preserved as the prior version.

---

## v2.2 → v2.3

**Problem.** §81 assumed API-key access fronted by a proxy; the operating environment uses provider account sign-in (Agent SDK credit model), with which a proxy is incompatible.
**Changes.** §81 rewritten as a dual-mode standard (Mode S subscription-auth ACTIVE; Mode P proxy DORMANT, activated by ADR); binding rows 8 and 22 re-mechanized; §82 item 8 (metering + concurrency) added; §85.6 credential custody updated; §86-C5 registered (shared identity, shared limits, policy volatility); §88 check 11 and §73 item 3 reworded; `prices.yaml` added to the seed kit.
**Compatibility.** Extends v2.2; evidence requirements unchanged — cost attribution shifts from billed to metered-estimated in Mode S, declared honestly rather than assumed. **Version.** 2.3.

---

## v2.3 → v2.4

**Problem.** Owner decision reversal: API keys adopted; the routing proxy is preferred as the active model-access mechanism.
**Changes.** §81 active/dormant labels swapped (Mode P ACTIVE, Mode S dormant fallback); §73 item 3 updated; §86-C5 marked dormant while Mode P is active. Dual-mode structure retained — flipping back is an ADR + policies.yaml change, per §81.
**Compatibility.** Extends v2.3; strengthens budget enforcement and cost attribution (hard per-agent caps, billed cost). **Version.** 2.4.

---

## v2.4 → v2.5

**Problem.** ADR-B000 (single machine identity) was approved and applied to the seed kit but never folded into this document: §80, §78 rows 4 and 19, and §88 checks 5–6 still described the three-bot design — and check 5 as written was structurally impossible under ADR-B000, since GitHub forbids a PR's author from reviewing its own PR. Separately, the Phase-0 sandbox findings (system-path bind mounts blocked) forced the bot PAT into the agent-readable workspace, contradicting §80.4 and BA-3 without a registered control; and §85.1 pinned a version floor to January/March CVE fixes long since superseded by the project's advisory cadence.
**Changes.** §80 rewritten per ADR-B000 (single identity + mandatory human review; three-identity upgrade path preserved); §78 rows 4 and 19 re-worded to match; §88 checks 5–6 re-worded to be executable under the single identity with attribution demonstrated; §86 gains C6 (gate-attribution risk, from ADR-B000) and C7 (workspace-resident bot PAT, from ADR-B002); §80.4 carries the C7 exception explicitly; §85.1 restated as latest-stable-at-provisioning with the named CVEs as minimum markers. Agent short-codes (ALE, LIN) do not occur in this document; see v1.3 and ADR-B001.
**Compatibility.** Extends v2.4. C7 converts a silent contradiction into a governed, registered control — the register-or-remove standard this Part exists to enforce. Required-review separation of duties is preserved and now correctly described. Nothing else weakened.
**Version.** 2.5. v2.4 preserved as the prior version.

---

## v2.5 → v2.6

**Problem.** Owner decision reversal — the second on this axis: subscriptions replace API keys as the funding reality; keys become an approval-gated fallback. §81 was already dual-mode, but the ACTIVE/DORMANT labels, §73 items 2–3, the kill-switch wording (§78 row 28, §88 check 13), and §86-C5's provider-policy history all encoded Mode P — and C5's history predated the June 15 pause.
**Changes.** §81 labels swapped per ADR-B003 (Mode S ACTIVE; Mode P dormant — reactivation requires an owner-approved ADR); §81 Mode S item 2 restated to the post-2026-06-15 reality (plan limits as the ceiling; the announced Agent SDK credit split paused; dispatcher metering is the budget mechanism of record); §73 items 2–3 updated (item 2 also corrected to the ADR-B000 single identity, missed in v2.5); §78 row 28 and §88 check 13 made mode-aware; §86-C5 history corrected to the four 2026 policy moves and status set ACTIVE while Mode S is declared.
**Compatibility.** Extends v2.5. Mirrors the v2.3→v2.4 flip in reverse, using the dual-mode machinery built for exactly this. Budget enforcement shifts from proxy hard caps to dispatcher metering + plan ceiling — declared honestly in C5, not assumed away. Nothing else weakened.
**Version.** 2.6. v2.5 preserved as the prior version.

---

## v2.6 → v2.7

**Problem.** §80.4 and §86-C7 described the bot credential as a fine-grained PAT (Contents + Pull requests RW). That token type is structurally impossible in this topology: GitHub fine-grained PATs cannot reach repositories their owner does not own, and `agenticfoundrybot` is a collaborator, not the owner — found 2026-07-16, when the bot's first push returned 404 on a repository it could not even see. The live credential has been a classic PAT (`repo` + `workflow`) since. The owner signed §86 in B0.4 with the discrepancy explicitly noted and the correction queued (`control/registers/`). Separately, §80 named only agent and owner identities, while the dispatcher's deploy key — an owner-approved, write-capable GitHub credential in daily use since 2026-07-17 — appeared nowhere in the identity standard.
**Changes.** §80.4 restated to the live credential (classic PAT, `repo` + `workflow`, 90-day, dual-home rotation) with the GitHub limitation, the account-hygiene bound, and the organization upgrade path recorded; §80 gains item 5 (infrastructure identity: dispatcher deploy key, `dispatcher@company.local` authorship, `dispatch/*` push path, independent revocability); §86-C7 restated to match, naming the `workflow`-scope escalation path, its current bound, and two new review triggers. ADR-B002 carries a corresponding amendment; its decision — token placement — is unchanged.
**Compatibility.** Extends v2.6. Corrective, not permissive: an inaccurate description of a control is replaced by an accurate one plus tighter, named mitigations and review triggers. No gate, review, or human-authority requirement changes; nothing is weakened. The register entry now states the scope the owner already signed for knowingly.
**Version.** 2.7. v2.6 preserved as the prior version.

---

**End of Version 2.7 — AI Operating System**
