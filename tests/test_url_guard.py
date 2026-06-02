"""Tests for the SSRF guard and the hardened URL fetch path."""

import os
import socket
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fact_checker import claims
from fact_checker.url_guard import UnsafeURLError, validate_public_url


def _fake_getaddrinfo(ip: str):
    """Return a getaddrinfo replacement that always resolves to ``ip``."""

    def _inner(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    return _inner


# --- Schemes -------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "gopher://example.com/x",
    "data:text/plain,hi",
])
def test_rejects_disallowed_schemes(url):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url)


def test_rejects_missing_host():
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://")


# --- Literal internal IPs (no DNS needed) --------------------------------

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://127.0.0.1:8501/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "http://[::1]/",
    "http://0.0.0.0/",
    "http://[::ffff:127.0.0.1]/",
])
def test_rejects_internal_ip_literals(url):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url)


# --- Hostname resolution -------------------------------------------------

def test_rejects_hostname_resolving_to_private(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("10.0.0.5"))
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://evil.example.com/")


def test_rejects_hostname_resolving_to_metadata(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("169.254.169.254"))
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://rebind.example.com/")


def test_allows_public_host(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    resolved = validate_public_url("https://example.com/article")
    assert resolved == {"93.184.216.34"}


def test_rejects_unresolvable_host(monkeypatch):
    def _boom(*args, **kwargs):
        raise socket.gaierror("nope")

    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://does-not-exist.example/")


# --- extract_claims_from_url short-circuits without fetching -------------

def test_extract_claims_blocks_internal_without_request(monkeypatch):
    called = {"hit": False}

    def _should_not_run(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("requests.get must not be called for a blocked URL")

    monkeypatch.setattr(claims.requests, "get", _should_not_run)

    result = claims.extract_claims_from_url("http://169.254.169.254/latest/meta-data/")

    assert result == []
    assert called["hit"] is False
