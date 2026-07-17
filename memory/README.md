# /memory — Role and Organizational Memory (B6.1, v2.1 §83)

| Namespace | Path | Reviewed by (CODEOWNERS) |
|---|---|---|
| Organizational | `memory/org/` | @msomali + @agenticfoundrybot (dual-control, ADR-B005) |
| Per-role | `memory/roles/<role>/` | @msomali + @agenticfoundrybot (dual-control, ADR-B005) |

**Write path (§83.1):** records enter this tree only through a reviewed PR —
this single rule implements the §29 write policy and the core of §32
poisoning defense. Project working memory is ordinary workspace files, never
this tree. OpenClaw session notes under `memory/` stay untracked by design
(.gitignore) — they are scratch, not memory records.

**Record format (§83.2):** one Markdown file per record, named
`<memory_id>.md`, with §28 front matter validated in CI by
`control/scripts/memory_lint.py` against `control/schemas/memory.json`.
`type: user_provided | observed | inferred | generated` is mandatory; write
only what is reusable, authorized, minimally sensitive, retention-defined,
and evidence-linked (§29).

**Read path (§83.3):** retrieval is by path/glob within the agent's
namespace; sensitivity rides on directory-level CODEOWNERS + repo
permissions. Memory cannot grant permission or override policy (§30).

**Forgetting (§83.4):** deletion = a PR that replaces the record's content
with tombstone front matter (`tombstone: true`, `purged_at`, `purge_reason`,
body reduced to the tombstone notice) + a run of
`control/scripts/memory_purge.py --id <memory_id>`, which clears any derived
index and verifies no live references remain. Supersession per v1 §52.4 via
`supersedes`/`superseded_by`.
