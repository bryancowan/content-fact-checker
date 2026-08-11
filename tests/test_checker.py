"""Tests for verdict judging and pipeline orchestration."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import checker


def _stub_search(monkeypatch, results=None):
    monkeypatch.setattr(checker, "search_web", lambda **kwargs: results or [])


# --- fact_check_single_claim: verdict normalization -----------------------


def test_fact_check_single_claim_normal_verdict(monkeypatch):
    _stub_search(monkeypatch)
    monkeypatch.setattr(
        checker,
        "call_cerebras_chat",
        lambda **kwargs: json.dumps(
            {"verdict": "true", "reason": "because", "top_sources": ["https://a.example"]}
        ),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.verdict == "true"
    assert result.reason == "because"
    assert result.sources == ["https://a.example"]


def test_fact_check_single_claim_invalid_verdict_falls_back_to_uncertain(monkeypatch):
    _stub_search(monkeypatch)
    monkeypatch.setattr(
        checker,
        "call_cerebras_chat",
        lambda **kwargs: json.dumps({"verdict": "maybe", "reason": "unclear", "top_sources": []}),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.verdict == "uncertain"


def test_fact_check_single_claim_malformed_json_falls_back(monkeypatch):
    _stub_search(monkeypatch)
    monkeypatch.setattr(checker, "call_cerebras_chat", lambda **kwargs: "not json at all")

    result = checker.fact_check_single_claim("some claim")

    assert result.verdict == "uncertain"
    assert result.reason == "Could not parse model output."
    assert result.sources == []


def test_fact_check_single_claim_truncates_sources_to_five(monkeypatch):
    _stub_search(monkeypatch)
    many_sources = [f"https://example.com/{i}" for i in range(10)]
    fake_payload = {"verdict": "true", "reason": "x", "top_sources": many_sources}
    monkeypatch.setattr(checker, "call_cerebras_chat", lambda **kwargs: json.dumps(fake_payload))

    result = checker.fact_check_single_claim("some claim")

    assert len(result.sources) == 5


def test_fact_check_single_claim_coerces_non_list_top_sources(monkeypatch):
    _stub_search(monkeypatch)
    monkeypatch.setattr(
        checker,
        "call_cerebras_chat",
        lambda **kwargs: json.dumps(
            {"verdict": "false", "reason": "x", "top_sources": "https://single.example"}
        ),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.sources == ["https://single.example"]


# --- fact_check_text orchestration -----------------------------------------


def test_fact_check_text_returns_empty_when_no_claims(monkeypatch):
    monkeypatch.setattr(checker, "extract_claims_from_text", lambda text, max_claims: [])

    result = checker.fact_check_text("nothing factual here")

    assert result == []


def test_fact_check_text_calls_on_progress_for_each_claim(monkeypatch):
    monkeypatch.setattr(checker, "extract_claims_from_text", lambda text, max_claims: ["c1", "c2"])
    _stub_search(monkeypatch)
    monkeypatch.setattr(
        checker,
        "call_cerebras_chat",
        lambda **kwargs: json.dumps({"verdict": "true", "reason": "x", "top_sources": []}),
    )

    progress_calls = []
    results = checker.fact_check_text(
        "text", on_progress=lambda msg, i, total: progress_calls.append((i, total))
    )

    assert len(results) == 2
    assert progress_calls == [(0, 2), (1, 2)]
