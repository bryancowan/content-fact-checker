"""Tests for claim extraction and its structured-output JSON parsing."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker import claims, config

# --- _parse_claims_json ---------------------------------------------------


def test_parse_claims_json_valid():
    raw = '{"claims": ["A", "B", "C"]}'
    assert claims._parse_claims_json(raw, max_claims=8) == ["A", "B", "C"]


def test_parse_claims_json_respects_max_claims():
    raw = '{"claims": ["A", "B", "C"]}'
    assert claims._parse_claims_json(raw, max_claims=2) == ["A", "B"]


def test_parse_claims_json_strips_blank_entries():
    raw = '{"claims": ["A", "  ", "", "B"]}'
    assert claims._parse_claims_json(raw, max_claims=8) == ["A", "B"]


def test_parse_claims_json_malformed_returns_empty():
    assert claims._parse_claims_json("not json", max_claims=8) == []


def test_parse_claims_json_missing_key_returns_empty():
    assert claims._parse_claims_json("{}", max_claims=8) == []


# --- extract_claims_from_text ---------------------------------------------


def test_extract_claims_from_text_uses_structured_output(monkeypatch):
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return '{"claims": ["Claim one"]}'

    monkeypatch.setattr(claims, "call_llm_chat", fake_call)

    result = claims.extract_claims_from_text("some article text", max_claims=5)

    assert result == ["Claim one"]
    assert captured["response_format"] == claims._CLAIMS_RESPONSE_FORMAT
    assert "image_data_urls" not in captured


# --- extract_claims_from_image ---------------------------------------------


def test_extract_claims_from_image_rejects_bad_mime_type():
    with pytest.raises(ValueError):
        claims.extract_claims_from_image(b"fake-bytes", "image/gif")


def test_extract_claims_from_image_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(claims, "MAX_IMAGE_BYTES", 10)
    with pytest.raises(ValueError):
        claims.extract_claims_from_image(b"x" * 11, "image/png")


def test_extract_claims_from_image_sends_data_uri_and_structured_output(monkeypatch):
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return '{"claims": ["Claim from image"]}'

    monkeypatch.setattr(claims, "call_llm_chat", fake_call)

    result = claims.extract_claims_from_image(b"\x89PNG", "image/png", max_claims=3)

    assert result == ["Claim from image"]
    assert captured["image_data_urls"][0].startswith("data:image/png;base64,")
    assert captured["response_format"] == claims._CLAIMS_RESPONSE_FORMAT


def test_long_text_is_truncated_before_the_model_call(monkeypatch):
    """The URL path can hand over a whole article; it must fit the context window."""
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return json.dumps({"claims": ["c"]})

    monkeypatch.setattr(claims, "call_llm_chat", fake_call)

    claims.extract_claims_from_text("x" * (config.MAX_ARTICLE_CHARS * 2))

    sent = captured["user_content"]
    assert "[Content truncated for length]" in sent
    # The article body is capped; the surrounding prompt template adds a little.
    assert "x" * config.MAX_ARTICLE_CHARS in sent
    assert "x" * (config.MAX_ARTICLE_CHARS + 1) not in sent


def test_short_text_is_not_truncated(monkeypatch):
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return json.dumps({"claims": ["c"]})

    monkeypatch.setattr(claims, "call_llm_chat", fake_call)

    claims.extract_claims_from_text("a short article")

    assert "[Content truncated for length]" not in captured["user_content"]


# --- URL fetching ----------------------------------------------------------


class _FakeRawBody:
    def __init__(self, payload):
        self._payload = payload

    def read(self, *args, **kwargs):
        return self._payload


class _FakeHTTPResponse:
    """Minimal stand-in for the streamed requests.Response _safe_get_text uses."""

    is_redirect = False
    is_permanent_redirect = False
    encoding = "utf-8"
    apparent_encoding = "utf-8"

    def __init__(self, payload):
        self.raw = _FakeRawBody(payload)

    def raise_for_status(self):
        return None

    def close(self):
        return None


def test_fetch_sends_a_user_agent(monkeypatch):
    """Without one, the default python-requests UA gets 403'd (e.g. Wikipedia),
    which would silently surface as "no claims found"."""
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return _FakeHTTPResponse(b"<html><body><p>" + b"word " * 50 + b"</p></body></html>")

    monkeypatch.setattr(claims, "validate_public_url", lambda url: None)
    monkeypatch.setattr(claims.requests, "get", fake_get)
    monkeypatch.setattr(claims, "extract_claims_from_text", lambda text, max_claims: ["c"])

    claims.extract_claims_from_url("https://example.com/article")

    assert captured["headers"]["User-Agent"] == config.HTTP_USER_AGENT
    assert "python-requests" not in captured["headers"]["User-Agent"]
