# Skill Review Checklist — v2.1 §85.5 (before vendoring anything into control/tools/skills/)
- [ ] Full source read; no external payload URLs or download-and-execute (curl|wget ... | sh)
- [ ] No prerequisite blocks instructing terminal actions or paste-site redirects
- [ ] No encoded blobs (base64/hex) without documented purpose
- [ ] No oversized padding intended to defeat scanners
- [ ] Declared tool needs mapped to TOOLS.yaml classes; least privilege
- [ ] Pinned by content hash; origin, reviewer, date recorded below
