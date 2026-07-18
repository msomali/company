"""slugify(title) — TASK-001 deliverable (PROJECT-000 dry run).

Acceptance criteria (task.yaml):
  - handles unicode folding (tests prove it)
  - trims separators (tests prove it)
  - property tests included and deterministic
"""
from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    """Fold `title` to a lowercase ascii slug.

    Unicode is folded via NFKD normalization with combining marks dropped
    (é → e, ü → u, ﬁ → fi); every run of non-alphanumeric characters
    collapses to a single hyphen; leading/trailing separators are trimmed.
    Deterministic and idempotent: slugify(slugify(x)) == slugify(x).
    """
    if not isinstance(title, str):
        raise TypeError(f"title must be str, got {type(title).__name__}")
    folded = unicodedata.normalize("NFKD", title)
    ascii_text = folded.encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM.sub("-", ascii_text).strip("-")
