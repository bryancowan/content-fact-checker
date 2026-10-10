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


def _get_int(key: str, default: int, minimum: int = 1, legacy_key: str | None = None) -> int:
    """Read an int setting from secrets/env.

    Falls back to default if the value is unset, unparseable, or below minimum.
    Out-of-range values are rejected rather than passed through: a rate limit of
    0, for example, would make RateLimiter index an empty deque and raise before
    any request was made.

    legacy_key is consulted when key is unset, so settings renamed from their
    CEREBRAS_* names keep working in existing deployments.
    """
    raw = _get_secret(key)
    if raw is None and legacy_key:
        raw = _get_secret(legacy_key)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return value if value >= minimum else default


CEREBRAS_API_KEY = _get_secret("CEREBRAS_API_KEY")
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
PARALLEL_API_KEY = _get_secret("PARALLEL_API_KEY")

# Which LLM provider serves chat completions. Switching is a config change only.
SUPPORTED_PROVIDERS = ("openai", "cerebras")
DEFAULT_PROVIDER = "openai"

# Overridable so a future deprecation is a config change, not a code change --
# gemma-4-31b (retired 2026-09-03) and zai-glm-4.7 (retired 2026-08-17) both
# forced a code edit here.
_DEFAULT_MODELS = {
    "openai": "gpt-6-luna",
    "cerebras": "qwen-3.8-27b",
}

# Both providers get "high": the Cerebras default already changed once between
# models (gemma-4-31b defaulted to "none"), and gpt-6-luna's own default is
# "medium", so it is pinned explicitly rather than inherited.
REASONING_EFFORT_ENV = {
    "openai": "OPENAI_REASONING_EFFORT",
    "cerebras": "CEREBRAS_REASONING_EFFORT",
}
_DEFAULT_REASONING_EFFORT = "high"


def resolve_provider(raw: str | None) -> str:
    """Normalise LLM_PROVIDER, failing loudly on a typo.

    An unrecognised value would otherwise fall through to the wrong SDK, with a
    confusing missing-key or unknown-model error far from the cause.
    """
    provider = (raw or DEFAULT_PROVIDER).strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM_PROVIDER {raw!r}; expected one of {', '.join(SUPPORTED_PROVIDERS)}."
        )
    return provider


def resolve_model_name(provider: str) -> str:
    """LLM_MODEL_NAME wins; the Cerebras-only legacy name is read for that provider."""
    explicit = _get_secret("LLM_MODEL_NAME")
    if not explicit and provider == "cerebras":
        explicit = _get_secret("CEREBRAS_MODEL_NAME")
    return explicit or _DEFAULT_MODELS[provider]


LLM_PROVIDER = resolve_provider(_get_secret("LLM_PROVIDER"))
LLM_MODEL_NAME = resolve_model_name(LLM_PROVIDER)

DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95

# Reasoning tokens count against the completion budget on both providers.
# Measured 2026-09-07 on qwen-3.8-27b: a simple verdict spends ~200 reasoning
# tokens, and claim extraction from a full-length article at MAX_ARTICLE_CHARS
# spends ~1,220 (1,333 completion tokens total). 16384 is ~12x that worst case --
# it is a cap rather than a reservation, so the headroom is free, and it stays
# well under both the 40k Cerebras paid-tier and 128k gpt-6-luna output ceilings.
DEFAULT_MAX_COMPLETION_TOKENS = _get_int(
    "LLM_MAX_COMPLETION_TOKENS", 16384, legacy_key="CEREBRAS_MAX_COMPLETION_TOKENS"
)

DEFAULT_REASONING_EFFORT = (
    _get_secret(REASONING_EFFORT_ENV[LLM_PROVIDER]) or _DEFAULT_REASONING_EFFORT
)
# Cerebras only. "parsed" keeps the reasoning trace out of message.content, so
# the structured JSON parsing in claims.py / checker.py keeps working. OpenAI
# rejects the parameter, and never returns the trace in message.content.
DEFAULT_REASONING_FORMAT = "parsed"

# Client-side pacing, applied to whichever provider is active. Cerebras allows
# 300 req/min on the paid Developer tier (5 on the free trial); OpenAI limits
# depend on the account tier, and its 429s are retried by the SDK regardless.
LLM_REQUESTS_PER_MIN = _get_int(
    "LLM_REQUESTS_PER_MIN", 300, legacy_key="CEREBRAS_REQUESTS_PER_MIN"
)

# Both SDKs already retry 408/409/429/5xx with retry-after-aware exponential
# backoff; these just widen their defaults (2 retries, 60s) for a slower,
# reasoning-enabled model.
LLM_MAX_RETRIES = _get_int("LLM_MAX_RETRIES", 5, minimum=0, legacy_key="CEREBRAS_MAX_RETRIES")
LLM_TIMEOUT_SECONDS = 120.0

# Image inputs: base64 PNG/JPEG data URIs only (no external URLs). The limits
# below are Cerebras's (qwen-3.8-27b): the binding one is 10 MiB on the *total
# request payload*, and base64 inflates bytes by ~4/3, so the per-image cap is
# set well below it. They are conservative for OpenAI, so they apply to both.
MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_TOTAL_REQUEST_BYTES = 10 * 1024 * 1024
MAX_IMAGES_PER_REQUEST = _get_int(
    "LLM_MAX_IMAGES_PER_REQUEST", 10, legacy_key="CEREBRAS_MAX_IMAGES_PER_REQUEST"
)
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}

# Identify ourselves when fetching article URLs. Sending no User-Agent gets the
# default python-requests string blocked outright by some sites (Wikipedia 403s
# it). Descriptive rather than browser-spoofing, per Wikipedia's UA policy.
HTTP_USER_AGENT = (
    _get_secret("HTTP_USER_AGENT")
    or "ContentFactChecker/1.0 (+https://github.com/bryancowan/content-fact-checker)"
)

# Cap article text sent for claim extraction. Measured 2026-09-07: 120k chars
# came to 28,998 prompt tokens, comfortably inside the 128k Cerebras paid
# context and far inside gpt-6-luna's 1.05M.
MAX_ARTICLE_CHARS = 120_000
