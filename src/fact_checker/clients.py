from cerebras.cloud.sdk import Cerebras
from openai import OpenAI
from parallel import Parallel

from .config import (
    CEREBRAS_API_KEY,
    LLM_MAX_RETRIES,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    PARALLEL_API_KEY,
)

_cerebras_client = None
_openai_client = None
_parallel_client = None


def get_cerebras_client() -> Cerebras:
    global _cerebras_client
    if _cerebras_client is None:
        if not CEREBRAS_API_KEY:
            raise RuntimeError(
                "CEREBRAS_API_KEY not set. Copy .env.example to .env and add your key, "
                "or set LLM_PROVIDER=openai."
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
                "or set LLM_PROVIDER=cerebras."
            )
        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            max_retries=LLM_MAX_RETRIES,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    return _openai_client


def get_llm_client():
    """Return the chat-completions client for the configured LLM_PROVIDER."""
    if LLM_PROVIDER == "cerebras":
        return get_cerebras_client()
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
