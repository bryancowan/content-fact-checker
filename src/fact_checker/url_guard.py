"""SSRF guard: validate that a user-supplied URL is safe to fetch.

A URL is "safe" only if it uses http(s) and every IP its host resolves to is a
normal, routable public address. This blocks loopback (127.0.0.1, ::1), the
RFC1918 private ranges, link-local (including the 169.254.169.254 cloud metadata
endpoint), and other reserved/multicast/unspecified space.

Known limitation — DNS-rebinding (TOCTOU):
    We resolve the host here to validate it, but the caller's ``requests.get``
    resolves the host again at connect time. An attacker controlling DNS for
    their domain (short TTL) could answer with a public IP during validation
    and a private IP at connect time, slipping through the gap between
    time-of-check and time-of-use.

    This is intentionally NOT closed. The exploit needs a hostile authoritative
    DNS server and a won timing race, and this fetch path only yields lossy,
    LLM-summarised claims rather than raw bytes — so the residual risk is low.
    If we ever harden further, the fix is to pin the connection to the IP we
    validated here (resolve once, connect to that exact IP while preserving the
    original Host header / TLS SNI, via a custom requests HTTPAdapter) so there
    is no second resolution to poison.
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(Exception):
    """Raised when a URL is malformed or resolves to a non-public address."""


def _check_ip(ip_str: str) -> None:
    """Raise UnsafeURLError if ip_str is not a routable public address."""
    ip = ipaddress.ip_address(ip_str)

    # Normalize IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) to the IPv4 address so
    # the range checks below catch it.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # covers 169.254.0.0/16 cloud metadata
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise UnsafeURLError(f"URL resolves to non-public address: {ip}")


def validate_public_url(url: str) -> set[str]:
    """Validate that ``url`` is safe to fetch.

    Returns the set of resolved IP strings (all confirmed public) on success.
    Raises UnsafeURLError on a bad scheme, missing host, resolution failure, or
    any resolved address in private/loopback/link-local/reserved space.
    """
    parsed = urlparse(url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Disallowed URL scheme: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no host")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve host {host!r}: {exc}") from exc

    if not addrinfo:
        raise UnsafeURLError(f"Could not resolve host {host!r}")

    resolved = {info[4][0] for info in addrinfo}
    for ip_str in resolved:
        _check_ip(ip_str)

    return resolved
