"""Tests for slugify — TASK-001 acceptance criteria.

Edge-case tests cover unicode folding and separator trimming; property
tests are deterministic (fixed-seed generator, no time/os dependence).
"""
from __future__ import annotations

import random
import re
import string
import sys
from pathlib import Path

import pytest

# Deliberate (SAT-53-F2): the dry-run project uses a bare src/ layout with
# no installable package, so the tests resolve the module via sys.path. If
# PROJECT-000 ever grows real packaging, replace this with an editable
# install and delete this block.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from slugify import slugify  # noqa: E402

SLUG_RE = re.compile(r"^$|^[a-z0-9]+(-[a-z0-9]+)*$")


# ------------------------------------------------------- unicode folding

@pytest.mark.parametrize("title,expected", [
    ("Crème Brûlée", "creme-brulee"),
    ("Über München", "uber-munchen"),
    ("naïve café", "naive-cafe"),
    ("ﬁne ﬂow", "fine-flow"),            # ligatures via NFKD
    ("São Paulo — Ávila", "sao-paulo-avila"),
    ("Ñandú niño", "nandu-nino"),
])
def test_unicode_folding(title, expected):
    assert slugify(title) == expected


# ---------------------------------------------------- separator trimming

@pytest.mark.parametrize("title,expected", [
    ("  Hello World  ", "hello-world"),
    ("--already-slugged--", "already-slugged"),
    ("...dots...and...runs...", "dots-and-runs"),
    ("__underscores__", "underscores"),
    ("Tabs\tand\nnewlines", "tabs-and-newlines"),
    ("multiple   spaces", "multiple-spaces"),
])
def test_trims_and_collapses_separators(title, expected):
    assert slugify(title) == expected


def test_empty_and_symbol_only_inputs():
    assert slugify("") == ""
    assert slugify("!!! *** !!!") == ""


# ------------------------------------- non-decomposable scripts (SAT-53-F1)
# Pins the documented known-limit contract from the implementation note:
# scripts without NFKD ascii decompositions drop out of the slug entirely.
# If the folding strategy ever changes (e.g. transliteration), these tests
# must be consciously rewritten alongside the note.

@pytest.mark.parametrize("title,expected", [
    ("Привет мир", ""),            # Cyrillic: whole string drops
    ("你好世界", ""),                  # CJK: whole string drops
    ("日本語のタイトル", ""),            # kana/kanji mix drops
    ("Café 北京", "cafe"),             # mixed script: Latin survives
    ("Москва Moscow 2026", "moscow-2026"),  # mixed: ascii+digits survive
])
def test_non_decomposable_scripts_drop_out(title, expected):
    assert slugify(title) == expected


def test_non_string_rejected():
    with pytest.raises(TypeError):
        slugify(None)


# ------------------------------------------------ property tests (seeded)

def _random_titles(n=500, seed=88):
    """Deterministic corpus: fixed seed, fixed alphabet, no ambient state."""
    rng = random.Random(seed)
    alphabet = (
        string.ascii_letters + string.digits + string.punctuation + " \t\n"
        + "éüñçøßæÉÜÑ—“”…áàâäíìîïóòôöúùûü"
    )
    for _ in range(n):
        yield "".join(
            rng.choice(alphabet) for _ in range(rng.randint(0, 40))
        )


@pytest.mark.parametrize("title", list(_random_titles()))
def test_property_output_shape(title):
    """Every output is empty or hyphen-separated lowercase ascii runs —
    hence no leading/trailing separators."""
    assert SLUG_RE.fullmatch(slugify(title))


def test_property_idempotent():
    for title in _random_titles():
        once = slugify(title)
        assert slugify(once) == once


def test_property_deterministic():
    for title in _random_titles():
        assert slugify(title) == slugify(title)
