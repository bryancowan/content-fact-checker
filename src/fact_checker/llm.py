import cerebras.cloud.sdk as cerebras_sdk
import openai

from .clients import get_llm_client
from .config import (
    DEFAULT_MAX_COMPLETION_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_REASONING_FORMAT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    LLM_MODEL_NAME,
    LLM_PROVIDER,
    MAX_IMAGES_PER_REQUEST,
    MAX_TOTAL_REQUEST_BYTES,
    REASONING_EFFORT_ENV,
)
from .rate_limiter import llm_rate_limiter

# Both SDKs expose the same exception names; catch either so llm.py doesn't
# need to know which one produced the error.
_NOT_FOUND_ERRORS = (cerebras_sdk.NotFoundError, openai.NotFoundError)
_RATE_LIMIT_ERRORS = (cerebras_sdk.RateLimitError, openai.RateLimitError)
_CONNECTION_ERRORS = (cerebras_sdk.APIConnectionError, openai.APIConnectionError)
_STATUS_ERRORS = (cerebras_sdk.APIStatusError, openai.APIStatusError)

_PROVIDER_LABELS = {"openai": "OpenAI", "cerebras": "Cerebras"}
_DEPRECATION_URLS = {
    "openai": "https://platform.openai.com/docs/deprecations",
    "cerebras": "https://inference-docs.cerebras.ai/support/deprecation",
}


class LLMCallError(RuntimeError):
    """A chat completion failed, or returned nothing usable."""


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


def _reasoning_and_sampling_kwargs(
    provider: str,
    temperature: float,
    top_p: float,
    reasoning_effort: str,
    reasoning_format: str,
) -> dict:
    """The request parameters that differ between providers.

    Cerebras takes temperature/top_p alongside reasoning, plus a
    reasoning_format that keeps the trace out of message.content.

    OpenAI's reasoning models reject temperature and top_p unless
    reasoning_effort is "none", and reject reasoning_format outright.
    """
    kwargs = {"reasoning_effort": reasoning_effort}
    if provider == "cerebras":
        kwargs.update(temperature=temperature, top_p=top_p, reasoning_format=reasoning_format)
    elif reasoning_effort == "none":
        kwargs.update(temperature=temperature, top_p=top_p)
    return kwargs


def call_llm_chat(
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
    """Call the chat completion API of the configured provider and model.

    If image_data_urls is provided, the user message is sent as a
    multimodal content array (text + one or more image_url blocks), the
    vision input format both providers share.

    If response_format is provided (e.g. a json_schema spec), it's passed
    through to constrain the model's output to that schema.

    Reasoning is on by default. On Cerebras, reasoning_format="parsed" keeps
    the reasoning trace in message.reasoning rather than message.content, so
    callers parsing structured JSON out of the return value see only the JSON.
    temperature, top_p and reasoning_format are only sent where the provider
    accepts them; see _reasoning_and_sampling_kwargs.

    Returns the model's response text. Raises LLMCallError if the API call
    fails or comes back with empty content.
    """
    provider = LLM_PROVIDER
    label = _PROVIDER_LABELS[provider]

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

    llm_rate_limiter.wait_if_needed()

    extra_kwargs = _reasoning_and_sampling_kwargs(
        provider, temperature, top_p, reasoning_effort, reasoning_format
    )
    if response_format is not None:
        extra_kwargs["response_format"] = response_format

    try:
        resp = get_llm_client().chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            **extra_kwargs,
        )
    except _NOT_FOUND_ERRORS as exc:
        # The signature of a retired model -- this app has been broken by
        # Cerebras deprecations twice already, so name the likely cause.
        raise LLMCallError(
            f"{label} rejected model {LLM_MODEL_NAME!r}. It may have been "
            f"deprecated; check {_DEPRECATION_URLS[provider]} and set "
            "LLM_MODEL_NAME to a current model."
        ) from exc
    except _RATE_LIMIT_ERRORS as exc:
        raise LLMCallError(
            f"{label} rate limit exceeded after retries. Lower "
            "LLM_REQUESTS_PER_MIN or wait before retrying."
        ) from exc
    except _CONNECTION_ERRORS as exc:
        raise LLMCallError(f"Could not reach the {label} API: {exc}") from exc
    except _STATUS_ERRORS as exc:
        raise LLMCallError(f"{label} API error: {exc}") from exc

    message = resp.choices[0].message
    # Structured outputs can come back as a refusal with content=None; naming it
    # beats the budget-exhausted message below, which would send you chasing the
    # wrong cause.
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise LLMCallError(f"{label} refused the request: {refusal}")

    content = message.content
    if not content or not content.strip():
        # Most likely the reasoning trace consumed the whole completion budget.
        # Fail loudly: callers would otherwise silently degrade to "no claims
        # found" or a verdict of "uncertain".
        raise LLMCallError(
            f"{label} returned empty content. The reasoning trace may have used "
            f"the entire {max_completion_tokens}-token completion budget; try "
            f"raising LLM_MAX_COMPLETION_TOKENS or lowering "
            f"{REASONING_EFFORT_ENV[provider]}."
        )
    return content
