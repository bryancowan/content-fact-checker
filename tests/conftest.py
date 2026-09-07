"""Test bootstrap.

These are offline unit tests for the SSRF guard and URL-fetch path. Importing the
``fact_checker`` package eagerly pulls in the Cerebras/Parallel SDKs via
``clients.py``; stub them so the tests run without those (heavy, network-only)
dependencies installed.
"""

import sys
import types


def _stub(name, **attrs):
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


_stub("cerebras")
_stub("cerebras.cloud")


class _StubAPIError(Exception):
    """Stand-in for the SDK's error hierarchy, which llm.py catches by type."""


_stub(
    "cerebras.cloud.sdk",
    Cerebras=object,
    APIStatusError=_StubAPIError,
    APIConnectionError=type("APIConnectionError", (_StubAPIError,), {}),
    NotFoundError=type("NotFoundError", (_StubAPIError,), {}),
    RateLimitError=type("RateLimitError", (_StubAPIError,), {}),
)
_stub("parallel", Parallel=object)
_stub("dotenv", load_dotenv=lambda *a, **k: None)
