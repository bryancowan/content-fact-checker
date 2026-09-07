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
    assert config.CEREBRAS_REQUESTS_PER_MIN >= 1
