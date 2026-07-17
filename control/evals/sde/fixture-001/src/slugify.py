"""Golden solution for SDE-GT-001 (FR-900): slugify(title)."""
from __future__ import annotations

import re
import unicodedata


def slugify(title: str) -> str:
    """Lowercase, ASCII-fold, and hyphen-join a title; trims separators."""
    folded = (
        unicodedata.normalize("NFKD", title)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
