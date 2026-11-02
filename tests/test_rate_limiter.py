"""Tests for the sliding-window rate limiter."""

import os
import sys
from collections import deque

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


class _AdmissionLog(deque):
    """A timestamps deque that logs each append: the limiter appends the admission time
    inside its lock, so the log is exact however the threads are scheduled afterwards."""

    def __init__(self, log):
        super().__init__()
        self._log = log

    def append(self, value):
        self._log.append(value)
        super().append(value)


def test_concurrent_callers_never_exceed_the_limit(monkeypatch):
    """An eval runs several models through the one shared limiter at once."""
    import threading

    clock, sleep_calls = _install_fake_clock(monkeypatch)
    limiter = RateLimiter(max_requests_per_minute=5)
    admitted = []
    limiter.timestamps = _AdmissionLog(admitted)

    threads = [threading.Thread(target=limiter.wait_if_needed) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stamps = sorted(admitted)
    assert len(stamps) == 20
    # No 60 s window ever holds more than 5 requests: each is at least a minute
    # after the one five places before it.
    assert all(stamps[i + 5] - stamps[i] >= 60 for i in range(len(stamps) - 5))
    assert sleep_calls
