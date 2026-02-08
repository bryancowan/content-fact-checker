import os
from dotenv import load_dotenv

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")

# Model configuration for zai-glm-4.7 on Cerebras
CEREBRAS_MODEL_NAME = "zai-glm-4.7"
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95
DEFAULT_MAX_TOKENS = 4096

# Free Tier rate limits
FREE_TIER_REQUESTS_PER_MIN = 10
