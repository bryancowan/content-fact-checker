"""Tests for the Cerebras chat-completion call wrapper."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import llm


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
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse("fake response")


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeCerebrasClient:
    def __init__(self):
        self.chat = _FakeChat()


def _install_fake_client(monkeypatch):
    fake_client = _FakeCerebrasClient()
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
