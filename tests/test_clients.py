"""Tests for provider dispatch and the OpenRouter client."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker import clients


@pytest.fixture(autouse=True)
def _reset_clients(monkeypatch):
    for name in ("_openai_client", "_openrouter_client", "_cerebras_client"):
        monkeypatch.setattr(clients, name, None)


def test_openrouter_client_uses_the_openai_sdk_on_openrouters_base_url(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(clients, "OpenAI", fake_openai)
    monkeypatch.setattr(clients, "OPENROUTER_API_KEY", "sk-or-test")

    clients.get_llm_client("openrouter")

    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["api_key"] == "sk-or-test"
    assert "HTTP-Referer" in captured["default_headers"]


def test_openrouter_without_a_key_names_the_missing_variable(monkeypatch):
    monkeypatch.setattr(clients, "OPENROUTER_API_KEY", None)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY not set"):
        clients.get_llm_client("openrouter")


def test_get_llm_client_routes_by_the_requested_provider(monkeypatch):
    sentinels = {"cerebras": object(), "openrouter": object(), "openai": object()}
    monkeypatch.setattr(clients, "get_cerebras_client", lambda: sentinels["cerebras"])
    monkeypatch.setattr(clients, "get_openrouter_client", lambda: sentinels["openrouter"])
    monkeypatch.setattr(clients, "get_openai_client", lambda: sentinels["openai"])
    monkeypatch.setattr(clients, "LLM_PROVIDER", "openai")

    for provider, sentinel in sentinels.items():
        assert clients.get_llm_client(provider) is sentinel
    assert clients.get_llm_client() is sentinels["openai"]
