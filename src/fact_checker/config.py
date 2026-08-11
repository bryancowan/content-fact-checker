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


CEREBRAS_API_KEY = _get_secret("CEREBRAS_API_KEY")
PARALLEL_API_KEY = _get_secret("PARALLEL_API_KEY")

# Model configuration for gemma-4-31b on Cerebras
CEREBRAS_MODEL_NAME = "gemma-4-31b"
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95
DEFAULT_MAX_TOKENS = 4096

# Free Tier rate limits (gemma-4-31b: 5 req/min, lower than glm-4.7's 10)
FREE_TIER_REQUESTS_PER_MIN = 5

# Image inputs: gemma-4-31b only accepts base64 PNG/JPEG data URIs
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}
