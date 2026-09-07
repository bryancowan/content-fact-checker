"""Tests for the Cerebras chat-completion call wrapper."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker import config, llm


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content="fake response"):
        self.calls = []
        self.content = content

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self.content)


class _FakeChat:
    def __init__(self, content="fake response"):
        self.completions = _FakeCompletions(content)


class _FakeCerebrasClient:
    def __init__(self, content="fake response"):
        self.chat = _FakeChat(content)


def _install_fake_client(monkeypatch, content="fake response"):
    fake_client = _FakeCerebrasClient(content)
    monkeypatch.setattr(llm, "get_cerebras_client", lambda: fake_client)
    monkeypatch.setattr(llm.cerebras_rate_limiter, "wait_if_needed", lambda: 0.0)
    return fake_client


def test_plain_text_message(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    result = llm.call_cerebras_chat(user_content="hello", system_content="sys")

    assert result == "fake response"
    [call] = fake_client.chat.completions.calls
    assert call["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    assert "response_format" not in call


def test_no_system_message_when_not_provided(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["messages"] == [{"role": "user", "content": "hi"}]


def test_image_message_uses_content_blocks(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(
        user_content="what is this?",
        image_data_urls=["data:image/png;base64,AAAA"],
    )

    [call] = fake_client.chat.completions.calls
    user_message = call["messages"][-1]
    assert user_message["role"] == "user"
    assert user_message["content"] == [
        {"type": "text", "text": "what is this?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]


def test_multiple_images_produce_multiple_blocks(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(
        user_content="compare these",
        image_data_urls=["data:image/png;base64,AAAA", "data:image/jpeg;base64,BBBB"],
    )

    [call] = fake_client.chat.completions.calls
    image_blocks = [b for b in call["messages"][-1]["content"] if b["type"] == "image_url"]
    assert len(image_blocks) == 2


def test_response_format_passed_through(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)
    schema = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {}}}

    llm.call_cerebras_chat(user_content="hi", response_format=schema)

    [call] = fake_client.chat.completions.calls
    assert call["response_format"] == schema


def test_rate_limiter_is_acquired_before_calling(monkeypatch):
    _install_fake_client(monkeypatch)
    calls = []

    def fake_wait():
        calls.append("waited")
        return 0.0

    monkeypatch.setattr(llm.cerebras_rate_limiter, "wait_if_needed", fake_wait)

    llm.call_cerebras_chat(user_content="hi")

    assert calls == ["waited"]


# --- model and request parameters -------------------------------------------


def test_configured_model_is_sent(monkeypatch):
    """Pin the model, so a swap can't pass a green suite while being wrong."""
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["model"] == "qwen-3.8-27b"
    assert call["model"] == config.CEREBRAS_MODEL_NAME


def test_reasoning_parameters_are_sent(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["reasoning_effort"] == "high"
    # "parsed" keeps the reasoning trace out of message.content, which the
    # structured-JSON callers depend on.
    assert call["reasoning_format"] == "parsed"


def test_uses_max_completion_tokens_and_not_max_tokens(monkeypatch):
    """max_tokens is deprecated, and sending both is an API error."""
    fake_client = _install_fake_client(monkeypatch)

    llm.call_cerebras_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["max_completion_tokens"] == config.DEFAULT_MAX_COMPLETION_TOKENS
    assert "max_tokens" not in call


# --- failure handling --------------------------------------------------------


def test_empty_content_raises_rather_than_returning_none(monkeypatch):
    """Reasoning can consume the whole budget; that must not degrade silently."""
    _install_fake_client(monkeypatch, content="")

    with pytest.raises(llm.CerebrasCallError, match="empty content"):
        llm.call_cerebras_chat(user_content="hi")


def test_none_content_raises(monkeypatch):
    _install_fake_client(monkeypatch, content=None)

    with pytest.raises(llm.CerebrasCallError):
        llm.call_cerebras_chat(user_content="hi")


# --- image limits ------------------------------------------------------------


def test_too_many_images_rejected(monkeypatch):
    _install_fake_client(monkeypatch)
    too_many = ["data:image/png;base64,AAAA"] * (config.MAX_IMAGES_PER_REQUEST + 1)

    with pytest.raises(ValueError, match="Too many images"):
        llm.call_cerebras_chat(user_content="hi", image_data_urls=too_many)


def test_images_over_total_payload_limit_rejected(monkeypatch):
    """The cap applies across the batch, not to each image alone."""
    _install_fake_client(monkeypatch)
    half = "data:image/png;base64," + ("A" * (config.MAX_TOTAL_REQUEST_BYTES // 2))

    with pytest.raises(ValueError, match="request payload limit"):
        llm.call_cerebras_chat(user_content="hi", image_data_urls=[half, half])
