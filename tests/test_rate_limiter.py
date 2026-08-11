"""Tests for the sliding-window rate limiter."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import rate_limiter as rate_limiter_module
from fact_checker.rate_limiter import RateLimiter


class _FakeClock:
    def __init__(self, start=1000.0):
        self.now = start

    def time(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _install_fake_clock(monkeypatch, start=1000.0):
    clock = _FakeClock(start)
    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)
        clock.advance(seconds)

    monkeypatch.setattr(rate_limiter_module.time, "time", clock.time)
    monkeypatch.setattr(rate_limiter_module.time, "sleep", fake_sleep)
    return clock, sleep_calls


def test_no_wait_under_limit(monkeypatch):
    clock, sleep_calls = _install_fake_clock(monkeypatch)
    limiter = RateLimiter(max_requests_per_minute=3)

    for _ in range(3):
        waited = limiter.wait_if_needed()
        assert waited == 0.0

    assert sleep_calls == []
    assert len(limiter.timestamps) == 3


def test_waits_when_over_limit(monkeypatch):
    clock, sleep_calls = _install_fake_clock(monkeypatch)
    limiter = RateLimiter(max_requests_per_minute=2)

    limiter.wait_if_needed()
    clock.advance(1)
    limiter.wait_if_needed()

    # Third call exceeds the limit within the 60s window and must wait.
    waited = limiter.wait_if_needed()

    assert waited > 0
    assert sleep_calls == [waited]
    assert len(limiter.timestamps) == 3


def test_old_timestamps_age_out(monkeypatch):
    clock, sleep_calls = _install_fake_clock(monkeypatch)
    limiter = RateLimiter(max_requests_per_minute=1)

    limiter.wait_if_needed()
    clock.advance(61)  # older than the 60s window

    waited = limiter.wait_if_needed()

    assert waited == 0.0
    assert sleep_calls == []
    assert len(limiter.timestamps) == 1
