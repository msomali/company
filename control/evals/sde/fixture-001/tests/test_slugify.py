"""Edge-case + property tests for SDE-GT-001."""
import random
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from slugify import slugify  # noqa: E402


def test_handles_unicode():
    assert slugify("Café déjà vu") == "cafe-deja-vu"


def test_trims_separators():
    assert slugify("  --Hello, World!--  ") == "hello-world"


def test_empty_and_symbol_only():
    assert slugify("") == ""
    assert slugify("!!!") == ""


def test_property_output_alphabet():
    rng = random.Random(84)  # deterministic — §84 evals never flake
    alphabet = string.printable + "éüßñç"
    for _ in range(200):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
        out = slugify(s)
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*|", out) is not None
        assert not out.startswith("-") and not out.endswith("-")


def test_property_idempotent():
    for s in ("Already-Slugged", "Mixed CASE Title", "a  b   c"):
        once = slugify(s)
        assert slugify(once) == once
