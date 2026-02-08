import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str | None:
    """Read a secret from Streamlit Cloud secrets (if available), else env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        pass
    return os.getenv(key)


CEREBRAS_API_KEY = _get_secret("CEREBRAS_API_KEY")
PARALLEL_API_KEY = _get_secret("PARALLEL_API_KEY")

# Model configuration for zai-glm-4.7 on Cerebras
CEREBRAS_MODEL_NAME = "zai-glm-4.7"
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95
DEFAULT_MAX_TOKENS = 4096

# Free Tier rate limits
FREE_TIER_REQUESTS_PER_MIN = 10
