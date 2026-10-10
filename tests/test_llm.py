"""Tests for the provider-switching chat-completion call wrapper."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cerebras.cloud.sdk as cerebras_sdk
import openai
import pytest

from fact_checker import config, llm


class _FakeMessage:
    def __init__(self, content, refusal=None):
        self.content = content
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, content, refusal=None):
        self.message = _FakeMessage(content, refusal)


class _FakeResponse:
    def __init__(self, content, refusal=None):
        self.choices = [_FakeChoice(content, refusal)]


class _FakeCompletions:
    def __init__(self, content="fake response", refusal=None, raises=None):
        self.calls = []
        self.content = content
        self.refusal = refusal
        self.raises = raises

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return _FakeResponse(self.content, self.refusal)


class _FakeChat:
    def __init__(self, content="fake response", refusal=None, raises=None):
        self.completions = _FakeCompletions(content, refusal, raises)


class _FakeClient:
    def __init__(self, content="fake response", refusal=None, raises=None):
        self.chat = _FakeChat(content, refusal, raises)


def _install_fake_client(
    monkeypatch, content="fake response", provider="openai", refusal=None, raises=None
):
    fake_client = _FakeClient(content, refusal, raises)
    monkeypatch.setattr(llm, "LLM_PROVIDER", provider)
    monkeypatch.setattr(llm, "get_llm_client", lambda: fake_client)
    monkeypatch.setattr(llm.llm_rate_limiter, "wait_if_needed", lambda: 0.0)
    return fake_client


def test_plain_text_message(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    result = llm.call_llm_chat(user_content="hello", system_content="sys")

    assert result == "fake response"
    [call] = fake_client.chat.completions.calls
    assert call["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    assert "response_format" not in call


def test_no_system_message_when_not_provided(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_llm_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["messages"] == [{"role": "user", "content": "hi"}]


def test_image_message_uses_content_blocks(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)

    llm.call_llm_chat(
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

    llm.call_llm_chat(
        user_content="compare these",
        image_data_urls=["data:image/png;base64,AAAA", "data:image/jpeg;base64,BBBB"],
    )

    [call] = fake_client.chat.completions.calls
    image_blocks = [b for b in call["messages"][-1]["content"] if b["type"] == "image_url"]
    assert len(image_blocks) == 2


def test_response_format_passed_through(monkeypatch):
    fake_client = _install_fake_client(monkeypatch)
    schema = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {}}}

    llm.call_llm_chat(user_content="hi", response_format=schema)

    [call] = fake_client.chat.completions.calls
    assert call["response_format"] == schema


def test_rate_limiter_is_acquired_before_calling(monkeypatch):
    _install_fake_client(monkeypatch)
    calls = []

    def fake_wait():
        calls.append("waited")
        return 0.0

    monkeypatch.setattr(llm.llm_rate_limiter, "wait_if_needed", fake_wait)

    llm.call_llm_chat(user_content="hi")

    assert calls == ["waited"]


# --- model and request parameters -------------------------------------------


def test_default_model_is_gpt_6_luna(monkeypatch):
    """Pin the model, so a swap can't pass a green suite while being wrong."""
    fake_client = _install_fake_client(monkeypatch)

    llm.call_llm_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["model"] == "gpt-6-luna"
    assert call["model"] == config.LLM_MODEL_NAME


def test_uses_max_completion_tokens_and_not_max_tokens(monkeypatch):
    """max_tokens is deprecated, and sending both is an API error."""
    for provider in config.SUPPORTED_PROVIDERS:
        fake_client = _install_fake_client(monkeypatch, provider=provider)

        llm.call_llm_chat(user_content="hi")

        [call] = fake_client.chat.completions.calls
        assert call["max_completion_tokens"] == config.DEFAULT_MAX_COMPLETION_TOKENS
        assert "max_tokens" not in call


def test_openai_defaults_to_high_reasoning_without_sampling_params(monkeypatch):
    """gpt-6 rejects temperature/top_p when reasoning is on, and reasoning_format always."""
    fake_client = _install_fake_client(monkeypatch, provider="openai")

    llm.call_llm_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["reasoning_effort"] == "high"
    assert "temperature" not in call
    assert "top_p" not in call
    assert "reasoning_format" not in call


def test_openai_sends_sampling_params_when_reasoning_is_none(monkeypatch):
    fake_client = _install_fake_client(monkeypatch, provider="openai")

    llm.call_llm_chat(user_content="hi", reasoning_effort="none", temperature=0.2, top_p=0.9)

    [call] = fake_client.chat.completions.calls
    assert call["reasoning_effort"] == "none"
    assert call["temperature"] == 0.2
    assert call["top_p"] == 0.9
    assert "reasoning_format" not in call


def test_cerebras_request_is_unchanged(monkeypatch):
    fake_client = _install_fake_client(monkeypatch, provider="cerebras")

    llm.call_llm_chat(user_content="hi")

    [call] = fake_client.chat.completions.calls
    assert call["reasoning_effort"] == "high"
    assert call["temperature"] == config.DEFAULT_TEMPERATURE
    assert call["top_p"] == config.DEFAULT_TOP_P
    # "parsed" keeps the reasoning trace out of message.content, which the
    # structured-JSON callers depend on.
    assert call["reasoning_format"] == "parsed"


# --- failure handling --------------------------------------------------------


def test_empty_content_raises_rather_than_returning_none(monkeypatch):
    """Reasoning can consume the whole budget; that must not degrade silently."""
    _install_fake_client(monkeypatch, content="")

    with pytest.raises(llm.LLMCallError, match="empty content"):
        llm.call_llm_chat(user_content="hi")


def test_none_content_raises(monkeypatch):
    _install_fake_client(monkeypatch, content=None)

    with pytest.raises(llm.LLMCallError):
        llm.call_llm_chat(user_content="hi")


def test_refusal_is_reported_as_a_refusal(monkeypatch):
    """A structured-output refusal has content=None; don't blame the token budget."""
    _install_fake_client(monkeypatch, content=None, refusal="I can't help with that.")

    with pytest.raises(llm.LLMCallError, match="refused the request: I can't help"):
        llm.call_llm_chat(user_content="hi")


@pytest.mark.parametrize(
    ("provider", "sdk", "label"),
    [("openai", openai, "OpenAI"), ("cerebras", cerebras_sdk, "Cerebras")],
)
@pytest.mark.parametrize(
    ("error_name", "match"),
    [
        ("NotFoundError", "rejected model"),
        ("RateLimitError", "LLM_REQUESTS_PER_MIN"),
        ("APIConnectionError", "Could not reach"),
        ("APIStatusError", "API error"),
    ],
)
def test_sdk_errors_become_llm_call_errors(monkeypatch, provider, sdk, label, error_name, match):
    error = getattr(sdk, error_name)("boom")
    _install_fake_client(monkeypatch, provider=provider, raises=error)

    with pytest.raises(llm.LLMCallError, match=match) as excinfo:
        llm.call_llm_chat(user_content="hi")

    assert label in str(excinfo.value)


# --- image limits ------------------------------------------------------------


def test_too_many_images_rejected(monkeypatch):
    _install_fake_client(monkeypatch)
    too_many = ["data:image/png;base64,AAAA"] * (config.MAX_IMAGES_PER_REQUEST + 1)

    with pytest.raises(ValueError, match="Too many images"):
        llm.call_llm_chat(user_content="hi", image_data_urls=too_many)


def test_images_over_total_payload_limit_rejected(monkeypatch):
    """The cap applies across the batch, not to each image alone."""
    _install_fake_client(monkeypatch)
    half = "data:image/png;base64," + ("A" * (config.MAX_TOTAL_REQUEST_BYTES // 2))

    with pytest.raises(ValueError, match="request payload limit"):
        llm.call_llm_chat(user_content="hi", image_data_urls=[half, half])
