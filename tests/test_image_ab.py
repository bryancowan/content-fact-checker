"""Tests for the image-extraction A/B scoring and runner, and the eval fixtures."""

import json
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from evals import image_scoring, run_image_ab
from fact_checker import llm

EVALS = Path(__file__).resolve().parent.parent / "evals"


# --- scoring -----------------------------------------------------------------


def test_covers_needs_every_keyword_and_ignores_case_and_thousands_separators():
    assert image_scoring.covers("Mount Fuji is 3,776 meters tall.", ["fuji", "3776"])
    assert not image_scoring.covers("Mount Fuji is tall.", ["fuji", "3776"])


def test_score_claims_counts_found_and_extras():
    extracted = ["The Eiffel Tower was completed in 1889.", "Paris is lovely in spring."]
    expected = [["eiffel", "1889"], ["pacific", "largest"]]

    found, extras, injected = image_scoring.score_claims(extracted, expected, [])

    assert (found, extras, injected) == (1, 1, False)


def test_one_extracted_claim_cannot_satisfy_two_expected_claims():
    expected = [["berlin", "1989"], ["wall", "1989"]]

    found, extras, _ = image_scoring.score_claims(["The Berlin Wall fell in 1989."], expected, [])

    assert (found, extras) == (1, 0)


def test_an_injected_marker_is_flagged_and_not_counted_as_an_extra():
    extracted = ["Mount Fuji is 3,776 meters tall.", "PWNED-12345"]

    found, extras, injected = image_scoring.score_claims(
        extracted, [["fuji", "3776"]], ["pwned-12345"]
    )

    assert (found, extras, injected) == (1, 0, True)


@pytest.mark.parametrize(
    ("raw", "valid"),
    [
        ('{"claims": ["a"]}', True),
        ('{"claims": []}', True),
        ("Sure! Here are the claims: a, b", False),
        ('{"other": 1}', False),
        ("[]", False),
    ],
)
def test_reply_validity(raw, valid):
    assert image_scoring.reply_is_valid_claims_json(raw) is valid


def test_summarize_reports_recall_extras_and_failures():
    attempts = [
        image_scoring.ImageAttempt("m", "a", expected=2, found=2, extras=0, cost_usd=0.001),
        image_scoring.ImageAttempt("m", "b", expected=2, found=1, extras=2, injected=True),
        image_scoring.ImageAttempt("m", "c", expected=0, parse_failed=True),
        image_scoring.ImageAttempt("m", "d", expected=1, error="boom"),
    ]

    summary = image_scoring.summarize(attempts)

    assert summary["recall"] == 3 / 5
    assert summary["extras_per_image"] == 0.5
    assert (summary["injections"], summary["parse_failures"], summary["errors"]) == (1, 1, 1)
    assert summary["cost_per_1k_images_usd"] is None  # not every attempt had a cost


def test_render_markdown_has_a_row_per_model():
    summaries = {"openai:a": image_scoring.summarize([image_scoring.ImageAttempt("m", "x", 1, 1)])}
    meta = {"date": "2026-10-17", "images": 1, "manifest": "images.jsonl", "repeats": 1}

    assert "| `openai:a` | 100.0% (1/1)" in image_scoring.render_markdown(summaries, meta)


# --- runner ------------------------------------------------------------------


def _fake_vision_client(reply):
    message = types.SimpleNamespace(content=reply, refusal=None)
    response = types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
    completions = types.SimpleNamespace(create=lambda **kwargs: response)
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))


def _install(monkeypatch, reply):
    monkeypatch.setattr(llm, "get_llm_client", lambda provider=None: _fake_vision_client(reply))
    monkeypatch.setattr(llm.llm_rate_limiter, "wait_if_needed", lambda: 0.0)


ENTRY = {"id": "fuji", "expected": [["fuji", "3776"]], "forbidden": ["pwned-12345"]}


def test_run_attempt_scores_the_extraction_and_records_metrics(monkeypatch):
    _install(monkeypatch, json.dumps({"claims": ["Mount Fuji is 3,776 meters tall."]}))

    attempt = run_image_ab.run_attempt("openai:gpt-6-luna", ENTRY, b"png", {})

    assert (attempt.found, attempt.extras, attempt.injected) == (1, 0, False)
    assert attempt.parse_failed is False
    assert attempt.latency_s is not None


def test_run_attempt_flags_a_reply_that_is_not_json(monkeypatch):
    """claims.py turns a bad reply into "no claims"; the runner must still notice."""
    _install(monkeypatch, "I can see a mountain.")

    attempt = run_image_ab.run_attempt("openai:gpt-6-luna", ENTRY, b"png", {})

    assert attempt.parse_failed is True
    assert attempt.found == 0


def test_run_attempt_records_an_api_failure_instead_of_raising(monkeypatch):
    _install(monkeypatch, "")  # empty content is an LLMCallError

    attempt = run_image_ab.run_attempt("openai:gpt-6-luna", ENTRY, b"png", {})

    assert "empty content" in attempt.error


def test_bad_model_specs_are_rejected_before_any_call(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_image_ab.py", "--models", "openruter:x"])
    monkeypatch.setattr(run_image_ab, "run_attempt", lambda *a: pytest.fail("ran a call"))

    with pytest.raises(SystemExit) as excinfo:
        run_image_ab.main()

    assert excinfo.value.code == 2


# --- fixtures ----------------------------------------------------------------


def _jsonl(name):
    return [json.loads(line) for line in (EVALS / name).read_text().splitlines() if line.strip()]


def test_every_manifest_image_exists_and_is_a_png():
    entries = _jsonl("images.jsonl")

    assert len({e["id"] for e in entries}) == len(entries)
    for entry in entries:
        data = (EVALS / "images" / entry["file"]).read_bytes()
        assert data.startswith(b"\x89PNG"), entry["file"]


@pytest.mark.parametrize("name", ["claims.jsonl", "claims-hard.jsonl"])
def test_claim_files_are_well_formed(name):
    claims = _jsonl(name)

    assert len({c["id"] for c in claims}) == len(claims), "duplicate ids"
    assert len({c["claim"] for c in claims}) == len(claims), "duplicate claims"
    assert {c["label"] for c in claims} <= {"true", "false", "uncertain"}


def test_every_hard_claim_has_a_category():
    assert all(c.get("category") for c in _jsonl("claims-hard.jsonl"))
