from cerebras.cloud.sdk import Cerebras
from parallel import Parallel

from .config import (
    CEREBRAS_API_KEY,
    CEREBRAS_MAX_RETRIES,
    CEREBRAS_TIMEOUT_SECONDS,
    PARALLEL_API_KEY,
)

_cerebras_client = None
_parallel_client = None


def get_cerebras_client() -> Cerebras:
    global _cerebras_client
    if _cerebras_client is None:
        if not CEREBRAS_API_KEY:
            raise RuntimeError(
                "CEREBRAS_API_KEY not set. Copy .env.example to .env and add your key."
            )
        # The SDK retries 408/409/429/5xx itself with exponential backoff that
        # honours retry-after headers; widen its defaults rather than hand-rolling.
        _cerebras_client = Cerebras(
            api_key=CEREBRAS_API_KEY,
            max_retries=CEREBRAS_MAX_RETRIES,
            timeout=CEREBRAS_TIMEOUT_SECONDS,
        )
    return _cerebras_client


def get_parallel_client() -> Parallel:
    global _parallel_client
    if _parallel_client is None:
        if not PARALLEL_API_KEY:
            raise RuntimeError(
                "PARALLEL_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _parallel_client = Parallel(api_key=PARALLEL_API_KEY)
    return _parallel_client
