import os

from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str | None:
    """Read a secret from Streamlit Cloud secrets (if available), else env vars."""
    try:
        import streamlit as st

        val = st.secrets.get(key)
        if val is not None:
            return val
    except Exception:
        pass
    return os.getenv(key)


def _get_int(key: str, default: int) -> int:
    """Read an int setting from secrets/env, falling back to default if unset or invalid."""
    raw = _get_secret(key)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


CEREBRAS_API_KEY = _get_secret("CEREBRAS_API_KEY")
PARALLEL_API_KEY = _get_secret("PARALLEL_API_KEY")

# Model configuration for qwen-3.8-27b on Cerebras.
# Overridable so a future deprecation is a config change, not a code change --
# gemma-4-31b (retired 2026-09-03) and zai-glm-4.7 (retired 2026-08-17) both
# forced a code edit here.
CEREBRAS_MODEL_NAME = _get_secret("CEREBRAS_MODEL_NAME") or "qwen-3.8-27b"

DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95

# qwen-3.8-27b reasons by default at "high", and reasoning tokens count against
# the completion budget. Measured 2026-09-07: a simple verdict spends ~200
# reasoning tokens, and claim extraction from a full-length article at
# MAX_ARTICLE_CHARS spends ~1,220 (1,333 completion tokens total). 16384 is ~12x
# that worst case -- it is a cap rather than a reservation, so the headroom is
# free, and it stays well under the 40k paid-tier output ceiling.
DEFAULT_MAX_COMPLETION_TOKENS = _get_int("CEREBRAS_MAX_COMPLETION_TOKENS", 16384)

# Pinned explicitly rather than inherited: the provider default already changed
# once between models (gemma-4-31b defaulted to "none").
DEFAULT_REASONING_EFFORT = _get_secret("CEREBRAS_REASONING_EFFORT") or "high"
# "parsed" keeps the reasoning trace out of message.content, so the structured
# JSON parsing in claims.py / checker.py keeps working.
DEFAULT_REASONING_FORMAT = "parsed"

# Rate limits: 300 req/min on the paid Developer tier (5 on the free trial).
CEREBRAS_REQUESTS_PER_MIN = _get_int("CEREBRAS_REQUESTS_PER_MIN", 300)

# The SDK already retries 408/409/429/5xx with retry-after-aware exponential
# backoff; these just widen its defaults (2 retries, 60s) for a slower,
# reasoning-enabled model.
CEREBRAS_MAX_RETRIES = _get_int("CEREBRAS_MAX_RETRIES", 5)
CEREBRAS_TIMEOUT_SECONDS = 120.0

# Image inputs: qwen-3.8-27b accepts base64 PNG/JPEG data URIs only (no external
# URLs). The binding limit is 10 MiB on the *total request payload*, and base64
# inflates bytes by ~4/3, so the per-image cap is set well below it.
MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_TOTAL_REQUEST_BYTES = 10 * 1024 * 1024
MAX_IMAGES_PER_REQUEST = _get_int("CEREBRAS_MAX_IMAGES_PER_REQUEST", 10)
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}

# Identify ourselves when fetching article URLs. Sending no User-Agent gets the
# default python-requests string blocked outright by some sites (Wikipedia 403s
# it). Descriptive rather than browser-spoofing, per Wikipedia's UA policy.
HTTP_USER_AGENT = (
    _get_secret("HTTP_USER_AGENT")
    or "ContentFactChecker/1.0 (+https://github.com/bryancowan/content-fact-checker)"
)

# Cap article text sent for claim extraction. Measured 2026-09-07: 120k chars
# came to 28,998 prompt tokens, comfortably inside the 128k paid context.
MAX_ARTICLE_CHARS = 120_000
