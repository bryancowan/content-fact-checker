"""Tests for settings parsing in config.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from fact_checker import config


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("TEST_SETTING", raising=False)
    return monkeypatch


def test_returns_default_when_unset(env):
    assert config._get_int("TEST_SETTING", 300) == 300


def test_reads_a_valid_value(env):
    env.setenv("TEST_SETTING", "42")
    assert config._get_int("TEST_SETTING", 300) == 42


def test_tolerates_surrounding_whitespace(env):
    env.setenv("TEST_SETTING", "  42  ")
    assert config._get_int("TEST_SETTING", 300) == 42


def test_falls_back_when_unparseable(env):
    env.setenv("TEST_SETTING", "not-a-number")
    assert config._get_int("TEST_SETTING", 300) == 300


@pytest.mark.parametrize("value", ["0", "-1", "-500"])
def test_rejects_values_below_the_minimum(env, value):
    """A rate limit of 0 would make RateLimiter index an empty deque and raise."""
    env.setenv("TEST_SETTING", value)
    assert config._get_int("TEST_SETTING", 300) == 300


def test_minimum_is_configurable_so_zero_can_be_allowed(env):
    """max_retries=0 is legitimate: it means "do not retry"."""
    env.setenv("TEST_SETTING", "0")
    assert config._get_int("TEST_SETTING", 5, minimum=0) == 0


def test_rate_limit_default_is_positive():
    """Guards the specific regression: a non-positive rate limit crashes RateLimiter."""
    assert config.LLM_REQUESTS_PER_MIN >= 1


def test_legacy_key_is_used_when_the_new_key_is_unset(env):
    env.delenv("NEW_SETTING", raising=False)
    env.setenv("OLD_SETTING", "7")
    assert config._get_int("NEW_SETTING", 300, legacy_key="OLD_SETTING") == 7


def test_new_key_wins_over_the_legacy_key(env):
    env.setenv("NEW_SETTING", "9")
    env.setenv("OLD_SETTING", "7")
    assert config._get_int("NEW_SETTING", 300, legacy_key="OLD_SETTING") == 9


# --- provider and model selection -------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, "openai"), ("", "openai"), ("openai", "openai"), (" Cerebras ", "cerebras")],
)
def test_resolve_provider(raw, expected):
    assert config.resolve_provider(raw) == expected


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        config.resolve_provider("anthropic")


@pytest.fixture
def model_env(monkeypatch):
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)
    monkeypatch.delenv("CEREBRAS_MODEL_NAME", raising=False)
    return monkeypatch


def test_default_models(model_env):
    assert config.resolve_model_name("openai") == "gpt-6-luna"
    assert config.resolve_model_name("cerebras") == "qwen-3.8-27b"


def test_llm_model_name_overrides_the_default(model_env):
    model_env.setenv("LLM_MODEL_NAME", "gpt-6-sol")
    assert config.resolve_model_name("openai") == "gpt-6-sol"


def test_legacy_cerebras_model_name_applies_to_cerebras_only(model_env):
    """render.yaml pins CEREBRAS_MODEL_NAME; it must not hold the OpenAI default back."""
    model_env.setenv("CEREBRAS_MODEL_NAME", "qwen-future")
    assert config.resolve_model_name("cerebras") == "qwen-future"
    assert config.resolve_model_name("openai") == "gpt-6-luna"
