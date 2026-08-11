"""Tests for the Parallel web-search wrapper and evidence formatting."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import search as search_module
from fact_checker.search import build_evidence_context


class _FakeWebResult:
    def __init__(self, url, title, publish_date, excerpts):
        self.url = url
        self.title = title
        self.publish_date = publish_date
        self.excerpts = excerpts


class _FakeSearchResponse:
    def __init__(self, results):
        self.results = results


class _FakeParallelClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


# --- search_web: stable (non-beta) API shape -------------------------------


def test_search_web_calls_stable_search_api_with_advanced_settings(monkeypatch):
    fake_response = _FakeSearchResponse(
        [_FakeWebResult("https://a.example", "Title A", "2024-01-01", ["excerpt"])]
    )
    fake_client = _FakeParallelClient(fake_response)
    monkeypatch.setattr(search_module, "get_parallel_client", lambda: fake_client)

    results = search_module.search_web("some query", num=3, mode="advanced")

    assert results == [
        {
            "url": "https://a.example",
            "title": "Title A",
            "publish_date": "2024-01-01",
            "excerpts": ["excerpt"],
        },
    ]
    [call] = fake_client.calls
    assert call["search_queries"] == ["some query"]
    assert call["mode"] == "advanced"
    # These must be nested under advanced_settings, not passed as top-level
    # kwargs — that's the exact shape that broke when parallel-web went 0.x -> 1.x.
    assert call["advanced_settings"] == {
        "max_results": 3,
        "excerpt_settings": {"max_chars_per_result": 8000},
    }


def test_search_web_handles_missing_title_and_date(monkeypatch):
    fake_response = _FakeSearchResponse([_FakeWebResult("https://b.example", None, None, [])])
    fake_client = _FakeParallelClient(fake_response)
    monkeypatch.setattr(search_module, "get_parallel_client", lambda: fake_client)

    [result] = search_module.search_web("query")

    assert result["title"] is None
    assert result["publish_date"] is None
    assert result["excerpts"] == []


# --- build_evidence_context -------------------------------------------------


def test_build_evidence_context_formats_sources():
    results = [
        {
            "url": "https://a.example",
            "title": "A title",
            "publish_date": "2024-01-01",
            "excerpts": ["excerpt one", "excerpt two", "excerpt three"],
        },
    ]

    context = build_evidence_context(results)

    assert "[Source 1]" in context
    assert "A title" in context
    assert "https://a.example" in context
    assert "excerpt one" in context
    assert "excerpt two" in context
    assert "excerpt three" not in context  # only the first two excerpts are included


def test_build_evidence_context_falls_back_to_url_when_no_title():
    results = [{"url": "https://b.example", "title": None, "publish_date": None, "excerpts": []}]

    context = build_evidence_context(results)

    assert "Title: https://b.example" in context


def test_build_evidence_context_truncates_long_context():
    results = [
        {
            "url": f"https://c{i}.example",
            "title": f"T{i}",
            "publish_date": None,
            "excerpts": ["x" * 500],
        }
        for i in range(20)
    ]

    context = build_evidence_context(results, max_chars=200)

    assert len(context) <= 200 + len("\n\n[Context truncated for length]")
    assert context.endswith("[Context truncated for length]")


def test_build_evidence_context_empty_results():
    assert build_evidence_context([]) == ""
