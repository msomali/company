# Skill Review SOP — v2.1 §85.5 (finalized B6.2)

**Standing rule:** zero direct marketplace/ClawHub installs, ever (hardening
row 5). A capability arrives only by vendoring reviewed source into
`control/tools/skills/<name>/` through this SOP. Anything installed outside
this path is a §63 incident (tool misuse).

## Vendoring flow

1. **Fetch** the skill source at a specific commit/version into a review
   worktree (not the live skills path). Record origin URL + upstream commit.
2. **Review** the full source against the checklist below — every file,
   including assets and lockfiles. Reviewer must be able to explain what
   every executable line does; "opaque but probably fine" fails.
3. **Record** the review in the table at the bottom (origin, upstream ref,
   reviewer, date, verdict, sha256).
4. **Vendor** the reviewed copy to `control/tools/skills/<name>/` in a PR
   that includes the review row and the pin file
   (`control/tools/skills/<name>.sha256` over the vendored tree, computed
   with `find <dir> -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`).
5. **Updates re-enter at step 1** — an upstream bump is a fresh review of
   the diff plus re-pin; hash drift without a review row is a CI/incident
   matter.

## Checklist (all boxes or no vendor)

- [ ] Full source read; no external payload URLs or download-and-execute
      (`curl|wget … | sh`, install scripts fetching at runtime)
- [ ] No prerequisite blocks instructing terminal actions or paste-site
      redirects
- [ ] No encoded blobs (base64/hex) without documented purpose and decoded
      review
- [ ] No oversized padding / filler intended to defeat scanners
- [ ] Prompt-bearing files (SKILL.md etc.) reviewed for injection patterns —
      instructions addressed to the agent that exceed the skill's stated
      purpose (§32/§39)
- [ ] Declared tool needs mapped to `control/tools/TOOLS.yaml` classes;
      least privilege; no new tool classes introduced silently
- [ ] Pinned by content hash; origin, upstream ref, reviewer, date recorded

## Review log

| Skill | Origin (URL@ref) | Reviewer | Date | Verdict | sha256 (tree) |
|---|---|---|---|---|---|
| _none vendored — standing rule holds (0 installs as of 2026-07-17)_ | | | | | |
