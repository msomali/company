"""titlecase_id — derive a lowercase hyphen-joined identifier from a short title.

---
artifact_id: SDE-TASK-003-src-titlecase-id
task_id: TASK-003
project_id: PROJECT-000
role: SDE
status: DRAFT
version: 1.0.0
data_classification: internal
---
"""

import re

_NON_ALNUM_RUN = re.compile(r"[^a-z0-9]+")


def titlecase_id(s: str) -> str:
    """Return a lowercase, hyphen-joined identifier derived from ``s``.

    Rules:
    - ASCII letters are lowercased.
    - Runs of non-alphanumeric characters collapse to a single hyphen.
    - No leading or trailing hyphens.
    - Empty or whitespace-only input returns the empty string.

    Examples:
        >>> titlecase_id("Hello, World!")
        'hello-world'
        >>> titlecase_id("   ")
        ''
    """
    if not isinstance(s, str):
        raise TypeError(f"titlecase_id expects str, got {type(s).__name__}")
    return _NON_ALNUM_RUN.sub("-", s.lower()).strip("-")
