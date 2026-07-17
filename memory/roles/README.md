# memory/roles — Per-Role Namespaces (v2.1 §83)

One directory per role short-code (ADR-B001): `pjm/ saa/ uud/ sde/ sat/ sse/
dpc/ dce/ de/ aie/ tw/ ale/ lin/`. Directories are created by each role's
first reviewed memory PR — empty scaffolding is deliberately absent (no
record, no directory). Record format and lifecycle: see `memory/README.md`.
A record's `namespace` front-matter field must match its path
(`roles/<role>`), enforced by memory-lint.
