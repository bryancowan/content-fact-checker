from cerebras.cloud.sdk import Cerebras
from openai import OpenAI
from parallel import Parallel

from .config import (
    CEREBRAS_API_KEY,
    LLM_MAX_RETRIES,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    PARALLEL_API_KEY,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_cerebras_client = None
_openai_client = None
_openrouter_client = None
_parallel_client = None


def get_cerebras_client() -> Cerebras:
    global _cerebras_client
    if _cerebras_client is None:
        if not CEREBRAS_API_KEY:
            raise RuntimeError(
                "CEREBRAS_API_KEY not set. Copy .env.example to .env and add your key, "
                "or set LLM_PROVIDER to another provider."
            )
        # The SDK retries 408/409/429/5xx itself with exponential backoff that
        # honours retry-after headers; widen its defaults rather than hand-rolling.
        _cerebras_client = Cerebras(
            api_key=CEREBRAS_API_KEY,
            max_retries=LLM_MAX_RETRIES,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    return _cerebras_client


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Copy .env.example to .env and add your key, "
                "or set LLM_PROVIDER to another provider."
            )
        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            max_retries=LLM_MAX_RETRIES,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    return _openai_client


def get_openrouter_client() -> OpenAI:
    """OpenRouter speaks the OpenAI API, so this is the OpenAI SDK on another base URL."""
    global _openrouter_client
    if _openrouter_client is None:
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key, "
                "or set LLM_PROVIDER to another provider."
            )
        _openrouter_client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            max_retries=LLM_MAX_RETRIES,
            timeout=LLM_TIMEOUT_SECONDS,
            # Optional attribution, so the app shows up in OpenRouter's analytics.
            default_headers={
                "HTTP-Referer": "https://factchecker.bryancowan.com",
                "X-OpenRouter-Title": "Content Fact Checker",
            },
        )
    return _openrouter_client


def get_llm_client(provider: str | None = None):
    """Return the chat-completions client for a provider (default: LLM_PROVIDER)."""
    provider = provider or LLM_PROVIDER
    if provider == "cerebras":
        return get_cerebras_client()
    if provider == "openrouter":
        return get_openrouter_client()
    return get_openai_client()


def get_parallel_client() -> Parallel:
    global _parallel_client
    if _parallel_client is None:
        if not PARALLEL_API_KEY:
            raise RuntimeError(
                "PARALLEL_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _parallel_client = Parallel(api_key=PARALLEL_API_KEY)
    return _parallel_client
