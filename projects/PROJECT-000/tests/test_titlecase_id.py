"""Tests for titlecase_id.

---
artifact_id: SDE-TASK-003-tests-titlecase-id
task_id: TASK-003
project_id: PROJECT-000
role: SDE
status: DRAFT
version: 1.0.0
data_classification: internal
---
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from titlecase_id import titlecase_id


# Acceptance criterion 1: empty and whitespace-only input returns empty string
class TestEmptyInput:
    def test_empty_string(self):
        assert titlecase_id("") == ""

    @pytest.mark.parametrize("s", [" ", "   ", "\t", "\n", " \t\n  "])
    def test_whitespace_only(self, s):
        assert titlecase_id(s) == ""

    def test_punctuation_only(self):
        assert titlecase_id("!!! --- ???") == ""


# Acceptance criterion 2: lowercase + collapse non-alphanumeric runs to hyphens
class TestLowercaseAndCollapse:
    def test_ascii_letters_lowercased(self):
        assert titlecase_id("Hello World") == "hello-world"
        assert titlecase_id("ALLCAPS") == "allcaps"
        assert titlecase_id("MiXeD CaSe TiTlE") == "mixed-case-title"

    def test_single_space_becomes_hyphen(self):
        assert titlecase_id("a b") == "a-b"

    def test_run_of_spaces_collapses(self):
        assert titlecase_id("a    b") == "a-b"

    def test_mixed_nonalnum_run_collapses(self):
        assert titlecase_id("a -- b__c!!d") == "a-b-c-d"

    def test_punctuation_run_collapses(self):
        assert titlecase_id("Hello,   World!!!  Again") == "hello-world-again"

    def test_digits_preserved(self):
        assert titlecase_id("Version 2 Update 10") == "version-2-update-10"

    def test_already_valid_identifier_unchanged(self):
        assert titlecase_id("already-valid-id-42") == "already-valid-id-42"


# Acceptance criterion 3: no leading or trailing hyphens
class TestNoEdgeHyphens:
    @pytest.mark.parametrize(
        "s",
        [
            "  leading spaces",
            "trailing spaces  ",
            "  both sides  ",
            "---dashes---",
            "!?Hello World?!",
        ],
    )
    def test_no_leading_or_trailing_hyphen(self, s):
        result = titlecase_id(s)
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_exact_values(self):
        assert titlecase_id("  Hello World  ") == "hello-world"
        assert titlecase_id("---Hello---") == "hello"


class TestTypeErrors:
    @pytest.mark.parametrize("bad", [None, 42, ["a"], b"bytes"])
    def test_non_str_raises(self, bad):
        with pytest.raises(TypeError):
            titlecase_id(bad)
