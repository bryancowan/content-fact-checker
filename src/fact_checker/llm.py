from cerebras.cloud.sdk import (
    APIConnectionError,
    APIStatusError,
    NotFoundError,
    RateLimitError,
)

from .clients import get_cerebras_client
from .config import (
    CEREBRAS_MODEL_NAME,
    DEFAULT_MAX_COMPLETION_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_REASONING_FORMAT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    MAX_IMAGES_PER_REQUEST,
    MAX_TOTAL_REQUEST_BYTES,
)
from .rate_limiter import cerebras_rate_limiter


class CerebrasCallError(RuntimeError):
    """A Cerebras chat completion failed, or returned nothing usable."""


def _validate_images(image_data_urls: list[str]) -> None:
    """Check an image batch against the model's per-request limits.

    Enforced here rather than at the caller because the total-payload cap
    applies across every image in the request, not to each one alone.
    """
    if len(image_data_urls) > MAX_IMAGES_PER_REQUEST:
        raise ValueError(
            f"Too many images: {len(image_data_urls)}. "
            f"At most {MAX_IMAGES_PER_REQUEST} are allowed per request."
        )
    total_bytes = sum(len(url) for url in image_data_urls)
    if total_bytes > MAX_TOTAL_REQUEST_BYTES:
        raise ValueError(
            f"Encoded images total {total_bytes} bytes, over the "
            f"{MAX_TOTAL_REQUEST_BYTES} byte request payload limit."
        )


def call_cerebras_chat(
    user_content: str,
    system_content: str | None = None,
    image_data_urls: list[str] | None = None,
    response_format: dict | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    reasoning_format: str = DEFAULT_REASONING_FORMAT,
) -> str:
    """Call the Cerebras chat completion API using the configured model.

    If image_data_urls is provided, the user message is sent as a
    multimodal content array (text + one or more image_url blocks) per
    Cerebras' vision input format.

    If response_format is provided (e.g. a json_schema spec), it's passed
    through to constrain the model's output to that schema.

    Reasoning is on by default. reasoning_format="parsed" keeps the reasoning
    trace in message.reasoning rather than message.content, so callers parsing
    structured JSON out of the return value see only the JSON.

    Returns the model's response text. Raises CerebrasCallError if the API call
    fails or comes back with empty content.
    """
    messages = []
    if system_content:
        messages.append({"role": "system", "content": system_content})

    if image_data_urls:
        _validate_images(image_data_urls)
        user_message_content = [{"type": "text", "text": user_content}]
        for url in image_data_urls:
            user_message_content.append({"type": "image_url", "image_url": {"url": url}})
        messages.append({"role": "user", "content": user_message_content})
    else:
        messages.append({"role": "user", "content": user_content})

    cerebras_rate_limiter.wait_if_needed()

    extra_kwargs = {}
    if response_format is not None:
        extra_kwargs["response_format"] = response_format

    try:
        resp = get_cerebras_client().chat.completions.create(
            model=CEREBRAS_MODEL_NAME,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort,
            reasoning_format=reasoning_format,
            **extra_kwargs,
        )
    except NotFoundError as exc:
        # The signature of a retired model -- this app has been broken by
        # Cerebras deprecations twice already, so name the likely cause.
        raise CerebrasCallError(
            f"Cerebras rejected model {CEREBRAS_MODEL_NAME!r}. It may have been "
            "deprecated; check https://inference-docs.cerebras.ai/support/deprecation "
            "and set CEREBRAS_MODEL_NAME to a current model."
        ) from exc
    except RateLimitError as exc:
        raise CerebrasCallError(
            "Cerebras rate limit exceeded after retries. Lower "
            "CEREBRAS_REQUESTS_PER_MIN or wait before retrying."
        ) from exc
    except APIConnectionError as exc:
        raise CerebrasCallError(f"Could not reach the Cerebras API: {exc}") from exc
    except APIStatusError as exc:
        raise CerebrasCallError(f"Cerebras API error: {exc}") from exc

    content = resp.choices[0].message.content
    if not content or not content.strip():
        # Most likely the reasoning trace consumed the whole completion budget.
        # Fail loudly: callers would otherwise silently degrade to "no claims
        # found" or a verdict of "uncertain".
        raise CerebrasCallError(
            "Cerebras returned empty content. The reasoning trace may have used "
            f"the entire {max_completion_tokens}-token completion budget; try "
            "raising CEREBRAS_MAX_COMPLETION_TOKENS or lowering "
            "CEREBRAS_REASONING_EFFORT."
        )
    return content
