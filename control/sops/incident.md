# Incident SOP — v2 §63 / v2.1 §78-28. SKELETON (finalized in B6.2).
1. Detect/report → open INC-### with timestamp, reporter, class (v2 §63 list).
2. Contain: run kill switch (stop sessions/containers, revoke proxy keys, freeze protected branches).
3. Preserve: snapshot episode packages, transcripts, proxy logs; no cleanup before capture.
4. If any secret value exposed (POL-009): rotate immediately; record rotation evidence.
5. Rollback via git revert / prior release tag; verify.
6. Communicate per v1.1 §55 (human sends).
7. Post-incident: lesson record; new eval case; §86 register review if a C-item was involved.
