"""Golden solution — slugify per the TASK-001 post-SAT contract.

CHECK-14 GREEN LEG: the separator trim is restored; the golden task passes
its tests and eval CI (and the lint eval-suite guard) go green.
"""
from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    if not isinstance(title, str):
        raise TypeError(f"title must be str, got {type(title).__name__}")
    folded = unicodedata.normalize("NFKD", title)
    ascii_text = folded.encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM.sub("-", ascii_text).strip("-")
