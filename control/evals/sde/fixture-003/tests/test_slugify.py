"""Golden-task tests — TASK-001 post-SAT contract (SAT-53-F1 included)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from slugify import slugify  # noqa: E402


def test_unicode_folding():
    assert slugify("Crème Brûlée") == "creme-brulee"
    assert slugify("Über München") == "uber-munchen"


def test_trims_separators():
    assert slugify("  Hello World  ") == "hello-world"
    assert slugify("--already-slugged--") == "already-slugged"


def test_non_decomposable_scripts_drop_out():
    # SAT-53-F1 pinned contract
    assert slugify("Привет мир") == ""
    assert slugify("你好世界") == ""
    assert slugify("Café 北京") == "cafe"


def test_idempotent():
    for title in ("Crème Brûlée", "  x  ", "Café 北京"):
        once = slugify(title)
        assert slugify(once) == once
