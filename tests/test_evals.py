"""Tests for the A/B scoring in evals/scoring.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from evals import scoring
from evals.scoring import Attempt


def _attempt(label, verdict, claim_id="c1", **kwargs):
    return Attempt(model="m", claim_id=claim_id, label=label, verdict=verdict, **kwargs)


def test_parse_model_spec_splits_on_the_first_colon_only():
    assert scoring.parse_model_spec("openai:gpt-6-luna") == ("openai", "gpt-6-luna")
    assert scoring.parse_model_spec("openrouter:nvidia/x:free") == ("openrouter", "nvidia/x:free")


@pytest.mark.parametrize("spec", ["gpt-6-luna", ":model", "openai:"])
def test_parse_model_spec_rejects_malformed_specs(spec):
    with pytest.raises(ValueError, match="provider:model"):
        scoring.parse_model_spec(spec)


def test_price_tokens():
    pricing = {"input_per_m": 0.25, "output_per_m": 1.0}
    assert scoring.price_tokens(1_000_000, 500_000, pricing) == pytest.approx(0.75)


@pytest.mark.parametrize(
    ("prompt", "completion", "pricing"),
    [
        (None, 10, {"input_per_m": 1, "output_per_m": 1}),
        (10, 10, None),
        (10, 10, {"input_per_m": None, "output_per_m": None}),
    ],
)
def test_price_tokens_is_none_when_anything_is_unknown(prompt, completion, pricing):
    assert scoring.price_tokens(prompt, completion, pricing) is None


def test_percentile_uses_nearest_rank():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert scoring.percentile(values, 50) == 5.0
    assert scoring.percentile(values, 95) == 10.0
    assert scoring.percentile([], 95) is None


def test_failed_calls_and_unparsed_answers_count_as_wrong_but_separately():
    attempts = [
        _attempt("true", "true"),
        _attempt("false", "true"),
        _attempt("true", "uncertain", parse_failed=True),
        _attempt("true", None, error="rate limit"),
    ]

    summary = scoring.summarize(attempts)

    assert summary["accuracy"] == 0.25
    assert summary["parse_failures"] == 1
    assert summary["errors"] == 1


def test_a_parse_fallback_that_matches_the_label_is_not_credited():
    """The fallback is "uncertain"; it must not score as a right answer on an uncertain claim."""
    summary = scoring.summarize([_attempt("uncertain", "uncertain", parse_failed=True)])

    assert summary["correct"] == 0
    assert summary["confusion"]["uncertain"]["unparsed"] == 1


def test_precision_and_recall_ignore_unparsed_and_errored_attempts():
    attempts = [
        _attempt("true", "true"),
        _attempt("false", "true"),
        _attempt("true", "uncertain", parse_failed=True),
    ]

    true_class = scoring.summarize(attempts)["per_class"]["true"]

    assert true_class["precision"] == 0.5
    assert true_class["recall"] == 0.5


def test_consistency_is_the_share_of_claims_whose_repeats_agree():
    attempts = [
        _attempt("true", "true", claim_id="a"),
        _attempt("true", "true", claim_id="a"),
        _attempt("true", "true", claim_id="b"),
        _attempt("true", "false", claim_id="b"),
    ]

    assert scoring.summarize(attempts)["consistency"] == 0.5


def test_cost_is_unknown_unless_every_attempt_has_one():
    known = scoring.summarize([_attempt("true", "true", cost_usd=0.5)] * 2)
    partial = scoring.summarize([_attempt("true", "true", cost_usd=0.5), _attempt("true", "true")])

    assert known["cost_per_1k_claims_usd"] == pytest.approx(500.0)
    assert known["cost_per_correct_usd"] == pytest.approx(0.5)
    assert partial["cost_per_1k_claims_usd"] is None


def test_render_markdown_has_a_row_per_model():
    summaries = {
        "openai:a": scoring.summarize([_attempt("true", "true", cost_usd=0.001, latency_s=2.0)]),
        "openrouter:b": scoring.summarize([_attempt("true", "false")]),
    }
    meta = {
        "date": "2026-10-17",
        "claims": 1,
        "label_counts": "1 true",
        "claims_file": "claims.jsonl",
        "repeats": 1,
    }

    report = scoring.render_markdown(summaries, meta)

    assert "| `openai:a` | 100.0% (1/1)" in report
    assert "| `openrouter:b` | 0.0% (0/1)" in report
    assert "n/a" in report  # no cost or latency for the second model


def test_category_accuracy_is_tallied_and_reported():
    attempts = [
        _attempt("true", "true", category="numeric"),
        _attempt("true", "false", category="numeric"),
        _attempt("false", "false", category="compound"),
        _attempt("false", "false"),  # a claims file without categories
    ]

    summary = scoring.summarize(attempts)

    assert summary["categories"] == {
        "numeric": {"attempts": 2, "correct": 1},
        "compound": {"attempts": 1, "correct": 1},
    }
    meta = {
        "date": "2026-10-17",
        "claims": 4,
        "label_counts": "2 true",
        "claims_file": "claims-hard.jsonl",
        "repeats": 1,
    }
    report = scoring.render_markdown({"openai:a": summary}, meta)
    assert "## Accuracy by category" in report
    assert "50.0% (1/2)" in report


def test_report_omits_the_category_table_when_claims_have_none():
    summary = scoring.summarize([_attempt("true", "true")])
    meta = {
        "date": "2026-10-17",
        "claims": 1,
        "label_counts": "1 true",
        "claims_file": "claims.jsonl",
        "repeats": 1,
    }

    assert "Accuracy by category" not in scoring.render_markdown({"m": summary}, meta)
