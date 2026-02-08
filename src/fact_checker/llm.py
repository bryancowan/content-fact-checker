from .clients import get_cerebras_client
from .config import CEREBRAS_MODEL_NAME, DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_MAX_TOKENS
from .rate_limiter import cerebras_rate_limiter


def call_cerebras_chat(
    user_content: str,
    system_content: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Call the Cerebras chat completion API using zai-glm-4.7.

    Returns the model's response text.
    """
    messages = []
    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": user_content})

    cerebras_rate_limiter.wait_if_needed()

    resp = get_cerebras_client().chat.completions.create(
        model=CEREBRAS_MODEL_NAME,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content
