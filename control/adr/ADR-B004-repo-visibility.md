---
artifact_id: control/adr/ADR-B004-repo-visibility.md
title: ADR-B004 — Repo public pending Pro (time-boxed)
type: adr
project: control
owner: human-owner
contributors: [human-owner]
reviewers: [bootstrap]
version: "1.0"
status: APPROVED
sensitivity: internal
created: 2026-07-16
updated: 2026-07-16
approval: owner (PR #2, merged 2026-07-16)
---

# ADR-B004 — Repo public pending Pro (time-boxed)
Decision: msomali/company remains public so branch protection (required review,
enforce_admins) stays enforceable at zero cost; owner declines Pro for now.
Accepted exposure: governance docs, evidence file (no secret values), PROJECT-001 charter.
Hard triggers to flip private+Pro, whichever first: (a) before the arf-care BASELINE
import (§57.2), (b) before any commercially sensitive artifact, (c) owner discretion.
Flipping private without Pro is prohibited — it silently disables protection.
Status: APPROVED, owner.
