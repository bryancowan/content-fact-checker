import contextlib
import contextvars
import time
from dataclasses import dataclass

import cerebras.cloud.sdk as cerebras_sdk
import openai

from .clients import get_llm_client
from .config import (
    DEFAULT_MAX_COMPLETION_TOKENS,
    DEFAULT_REASONING_FORMAT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    LLM_MODEL_NAME,
    LLM_PROVIDER,
    MAX_IMAGES_PER_REQUEST,
    MAX_TOTAL_REQUEST_BYTES,
    REASONING_EFFORT_ENV,
    resolve_reasoning_effort,
)
from .rate_limiter import llm_rate_limiter

# Both SDKs expose the same exception names; catch either so llm.py doesn't
# need to know which one produced the error.
_NOT_FOUND_ERRORS = (cerebras_sdk.NotFoundError, openai.NotFoundError)
_RATE_LIMIT_ERRORS = (cerebras_sdk.RateLimitError, openai.RateLimitError)
_CONNECTION_ERRORS = (cerebras_sdk.APIConnectionError, openai.APIConnectionError)
_STATUS_ERRORS = (cerebras_sdk.APIStatusError, openai.APIStatusError)

_PROVIDER_LABELS = {"openai": "OpenAI", "cerebras": "Cerebras", "openrouter": "OpenRouter"}
_DEPRECATION_URLS = {
    "openai": "https://platform.openai.com/docs/deprecations",
    "cerebras": "https://inference-docs.cerebras.ai/support/deprecation",
    "openrouter": "https://openrouter.ai/models",
}


class LLMCallError(RuntimeError):
    """A chat completion failed, or returned nothing usable."""


@dataclass
class LLMResult:
    """A completion's text plus what it cost to get.

    cost_usd is only filled when the provider reports it (OpenRouter does, as
    usage.cost); callers that need a cost for the others price the tokens.
    """

    text: str
    provider: str
    model: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None


# Provider and model are config read at import, so an A/B run can't switch them by
# editing env vars. llm_override() swaps them for the calls made inside the block
# -- including the ones deep in claims.py and checker.py -- without those modules
# having to thread a parameter through. A ContextVar keeps it per-thread/task.
_override: contextvars.ContextVar[tuple[str, str] | None] = contextvars.ContextVar(
    "llm_override", default=None
)
_recorder: contextvars.ContextVar[list[LLMResult] | None] = contextvars.ContextVar(
    "llm_recorder", default=None
)


@contextlib.contextmanager
def llm_override(provider: str, model: str):
    """Route every call_llm_chat inside the block to this provider and model."""
    if provider not in _PROVIDER_LABELS:
        raise ValueError(f"Unsupported provider {provider!r}.")
    token = _override.set((provider, model))
    try:
        yield
    finally:
        _override.reset(token)


@contextlib.contextmanager
def record_llm_calls():
    """Collect an LLMResult for each successful call made inside the block."""
    calls: list[LLMResult] = []
    token = _recorder.set(calls)
    try:
        yield calls
    finally:
        _recorder.reset(token)


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

    OpenRouter documents effort only as a "reasoning" object, so it goes in
    extra_body. It normalises reasoning to message.reasoning, so content stays
    pure JSON without a reasoning_format, and it drops sampling parameters a
    routed model doesn't support rather than erroring, so those are always sent.
    """
    if provider == "openrouter":
        return {
            "extra_body": {"reasoning": {"effort": reasoning_effort}},
            "temperature": temperature,
            "top_p": top_p,
        }
    kwargs = {"reasoning_effort": reasoning_effort}
    if provider == "cerebras":
        kwargs.update(temperature=temperature, top_p=top_p, reasoning_format=reasoning_format)
    elif reasoning_effort == "none":
        kwargs.update(temperature=temperature, top_p=top_p)
    return kwargs


def _token_counts(usage) -> tuple[int | None, int | None, int | None, float | None]:
    """Pull (prompt, completion, reasoning, cost) from a response's usage, if present."""
    if usage is None:
        return None, None, None, None
    details = getattr(usage, "completion_tokens_details", None)
    cost = getattr(usage, "cost", None)
    return (
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
        getattr(details, "reasoning_tokens", None),
        float(cost) if cost is not None else None,
    )


def call_llm_chat_with_metrics(
    user_content: str,
    system_content: str | None = None,
    image_data_urls: list[str] | None = None,
    response_format: dict | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    reasoning_effort: str | None = None,
    reasoning_format: str = DEFAULT_REASONING_FORMAT,
) -> LLMResult:
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

    The provider and model are the configured ones unless a llm_override()
    block is active. reasoning_effort defaults to that provider's setting.

    Returns an LLMResult carrying the response text, latency and token usage.
    Raises LLMCallError if the API call fails or comes back with empty content.
    """
    provider, model = _override.get() or (LLM_PROVIDER, LLM_MODEL_NAME)
    label = _PROVIDER_LABELS[provider]
    if reasoning_effort is None:
        reasoning_effort = resolve_reasoning_effort(provider)

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

    started = time.perf_counter()
    try:
        resp = get_llm_client(provider).chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            **extra_kwargs,
        )
    except _NOT_FOUND_ERRORS as exc:
        # The signature of a retired model -- this app has been broken by
        # Cerebras deprecations twice already, so name the likely cause.
        raise LLMCallError(
            f"{label} rejected model {model!r}. It may have been "
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

    latency_s = time.perf_counter() - started

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

    prompt_tokens, completion_tokens, reasoning_tokens, cost_usd = _token_counts(
        getattr(resp, "usage", None)
    )
    result = LLMResult(
        text=content,
        provider=provider,
        model=model,
        latency_s=latency_s,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        reasoning_tokens=reasoning_tokens,
        cost_usd=cost_usd,
    )
    if (calls := _recorder.get()) is not None:
        calls.append(result)
    return result


def call_llm_chat(
    user_content: str,
    system_content: str | None = None,
    image_data_urls: list[str] | None = None,
    response_format: dict | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    reasoning_effort: str | None = None,
    reasoning_format: str = DEFAULT_REASONING_FORMAT,
) -> str:
    """call_llm_chat_with_metrics, returning just the response text."""
    return call_llm_chat_with_metrics(
        user_content=user_content,
        system_content=system_content,
        image_data_urls=image_data_urls,
        response_format=response_format,
        temperature=temperature,
        top_p=top_p,
        max_completion_tokens=max_completion_tokens,
        reasoning_effort=reasoning_effort,
        reasoning_format=reasoning_format,
    ).text
