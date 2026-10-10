"""Tests for verdict judging and pipeline orchestration."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import checker


def _stub_search(monkeypatch, urls=()):
    """Stub search_web with results carrying the given URLs.

    Cited sources are validated against these, so a test asserting on
    result.sources must list the URLs it expects to survive.
    """
    results = [{"url": u, "title": None, "publish_date": None, "excerpts": []} for u in urls]
    monkeypatch.setattr(checker, "search_web", lambda **kwargs: results)


# --- fact_check_single_claim: verdict normalization -----------------------


def test_fact_check_single_claim_normal_verdict(monkeypatch):
    _stub_search(monkeypatch, ["https://a.example"])
    monkeypatch.setattr(
        checker,
        "call_llm_chat",
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
        "call_llm_chat",
        lambda **kwargs: json.dumps({"verdict": "maybe", "reason": "unclear", "top_sources": []}),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.verdict == "uncertain"


def test_fact_check_single_claim_malformed_json_falls_back(monkeypatch):
    _stub_search(monkeypatch)
    monkeypatch.setattr(checker, "call_llm_chat", lambda **kwargs: "not json at all")

    result = checker.fact_check_single_claim("some claim")

    assert result.verdict == "uncertain"
    assert result.reason == "Could not parse model output."
    assert result.sources == []


def test_fact_check_single_claim_truncates_sources_to_five(monkeypatch):
    many_sources = [f"https://example.com/{i}" for i in range(10)]
    _stub_search(monkeypatch, many_sources)
    fake_payload = {"verdict": "true", "reason": "x", "top_sources": many_sources}
    monkeypatch.setattr(checker, "call_llm_chat", lambda **kwargs: json.dumps(fake_payload))

    result = checker.fact_check_single_claim("some claim")

    assert len(result.sources) == 5


def test_fact_check_single_claim_coerces_non_list_top_sources(monkeypatch):
    _stub_search(monkeypatch, ["https://single.example"])
    monkeypatch.setattr(
        checker,
        "call_llm_chat",
        lambda **kwargs: json.dumps(
            {"verdict": "false", "reason": "x", "top_sources": "https://single.example"}
        ),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.sources == ["https://single.example"]


def test_fact_check_single_claim_drops_sources_not_in_evidence(monkeypatch):
    """A cited URL the search never returned is discarded.

    Covers both hallucinated citations and links injected via untrusted input.
    """
    _stub_search(monkeypatch, ["https://real.example"])
    monkeypatch.setattr(
        checker,
        "call_llm_chat",
        lambda **kwargs: json.dumps(
            {
                "verdict": "true",
                "reason": "x",
                "top_sources": ["https://real.example", "https://evil.example/phish"],
            }
        ),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.sources == ["https://real.example"]


def test_fact_check_single_claim_drops_non_http_sources(monkeypatch):
    _stub_search(monkeypatch, ["javascript:alert(1)"])
    monkeypatch.setattr(
        checker,
        "call_llm_chat",
        lambda **kwargs: json.dumps(
            {"verdict": "true", "reason": "x", "top_sources": ["javascript:alert(1)"]}
        ),
    )

    result = checker.fact_check_single_claim("some claim")

    assert result.sources == []


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
        "call_llm_chat",
        lambda **kwargs: json.dumps({"verdict": "true", "reason": "x", "top_sources": []}),
    )

    progress_calls = []
    results = checker.fact_check_text(
        "text", on_progress=lambda msg, i, total: progress_calls.append((i, total))
    )

    assert len(results) == 2
    assert progress_calls == [(0, 2), (1, 2)]
