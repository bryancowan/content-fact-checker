"""Tests for claim extraction and its structured-output JSON parsing."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker import claims

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

    monkeypatch.setattr(claims, "call_cerebras_chat", fake_call)

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

    monkeypatch.setattr(claims, "call_cerebras_chat", fake_call)

    result = claims.extract_claims_from_image(b"\x89PNG", "image/png", max_claims=3)

    assert result == ["Claim from image"]
    assert captured["image_data_urls"][0].startswith("data:image/png;base64,")
    assert captured["response_format"] == claims._CLAIMS_RESPONSE_FORMAT
