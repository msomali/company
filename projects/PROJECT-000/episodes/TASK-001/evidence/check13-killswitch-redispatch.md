# §88 check 13 — kill-switch pause/resume + re-dispatch from state (raw evidence)

- Date: 2026-07-18 (PDT); actors: H (pause/inspect/resume) + A (re-dispatch,
  fresh session); RUNBOOK-B7.2 v1.8 check-13 procedure (owner-vetted)
- Sever/freeze legs: evidenced 2026-07-17 (hardening row 9); this check
  adds the custody/re-dispatch leg only, per the runbook.

## Observable (i) — custody across hard stop (owner leg, ~20:32–20:47 PDT)

Owner-captured mid-pause: dispatcher `inactive`, gateway ECONNREFUSED,
containers none; `git show origin/dispatch/TASK-001:...state.yaml` read
`state: DEPLOYMENT` — the task existed only as committed state, owned by
no process. (Owner report 20:47 PDT; the bot session died with the
gateway at pause and this evidence file is written by the successor
session.) Full raw terminal capture archived verbatim:
`evidence/check13-owner-pause-capture.txt` (pause 20260719T033338Z →
resume 20260719T033649Z; incident dir
/var/company/incident-20260719T033338Z; owner-window steps 4/5 printed
but deliberately not executed per the drill design).

## Observable (ii) — re-dispatch from persisted state (fresh process)

Driver `check13_redispatch.py` (committed pre-run), verbatim output:

    pre-dispatch (from disk): state=DEPLOYMENT run_id=None iteration=0 history_entries=13
    observable: run_id recorded: PASS
    observable: iteration 0->1: PASS
    observable: history preserved: PASS
    observable: prompt has envelope from disk: PASS
    re-dispatched to sde [recorded-resume-001] from persisted state

- `state.yaml` diff: `run_id: null → recorded-resume-001`,
  `iteration_count: 0 → 1`, pre-pause history preserved verbatim.
- `log.jsonl` gained `{"event": "dispatch", "role": "SDE",
  "run_id": "recorded-resume-001"}`; committed as
  `TASK-001: dispatched to SDE [recorded-resume-001]`.
- Correction to the procedure text: it predicted a "14-entry" pre-pause
  history; the true count is 13 (arithmetic error in the procedure
  narrative, found at run time). The preservation assertion compares the
  disk state against itself pre/post, so the property is unaffected.
- BA-2.4: manifest flip existed only in a TemporaryDirectory copy
  (`manifest_dir` injection); real manifests untouched (`git status`
  clean of manifest changes).

## Observable (iii) — prompt reconstructed from disk

`evidence/check13-redispatch-prompt.txt`: digest inline + TASK-001
envelope verbatim (`task_id: TASK-001`, slugify objective) — assembled by
a process whose only knowledge of the task came from the committed files.

## Observable (iv) — completion to terminal state

    OK -> PRODUCTION_VERIFICATION   [release merged: PR #61, f9bb463b; release branch lineage]
    OK -> OPERATIONS_AND_FEEDBACK   [episode evidence through check 12; post-fix cost report]
    OK -> CLOSED                    [dry-run task complete — terminal]
    final state: CLOSED (terminal: True) history_entries=16

"Completes" per the P2(b) grounding in the runbook: terminal state via
evidenced transitions, not real agent work (activation-era).

## Episode close-out

Collector re-run after the new files: §9 checklist required transcripts
once `model_calls: 2` existed — satisfied honestly with transcripts of
record for both session-attributed calls (`transcripts/call-1-sde.md`,
`call-2-sat.md`: actual prompt/deliverable/review-body content). Final:
`episode TASK-001: 29 file(s), complete`; `--check` green.

- Result: **PASS** — all four observables; TASK-001 CLOSED.
