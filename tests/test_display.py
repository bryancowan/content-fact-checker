"""Tests for escaping text before it reaches Streamlit's markdown renderer."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker.display import escape_dollars


def test_escapes_a_pair_of_prices():
    """The reported bug: "$5 ... $25" rendered as LaTeX with the dollars dropped."""
    text = "priced at $5 per million input tokens and $25 per million output tokens"
    assert escape_dollars(text) == (
        r"priced at \$5 per million input tokens and \$25 per million output tokens"
    )


def test_escapes_a_single_dollar():
    assert escape_dollars("costs $5") == r"costs \$5"


def test_escapes_adjacent_dollars():
    assert escape_dollars("$5/$25") == r"\$5/\$25"


@pytest.mark.parametrize(
    "text", ["", "no prices here", "50% off, 5 per million", "**bold** `code`"]
)
def test_leaves_text_without_dollars_unchanged(text):
    assert escape_dollars(text) == text


def test_is_idempotent():
    """An already-escaped dollar must not gain a second backslash."""
    once = escape_dollars("costs $5 and $25")
    assert escape_dollars(once) == once
