import os
from dotenv import load_dotenv

load_dotenv()

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

GNEWS_URL = "https://gnews.io/api/v4/search"

# Keep this configurable in case the model changes.
# Model names change often. If Gemini returns 404 "no longer available",
# set GEMINI_MODEL in .env to the model name the error message recommends.
LLM_MODEL = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.8-flash"

# Set USE_GEMINI_CLASSIFIER=false in .env to classify queries locally only
# (no Gemini quota used for classification).
USE_GEMINI_CLASSIFIER = (
    os.getenv("USE_GEMINI_CLASSIFIER", "true").strip().lower()
    not in {"false", "0", "no", "off"}
)


def validate_api_keys():
    """Return the names of API keys that are missing."""
    required = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GNEWS_API_KEY": GNEWS_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "TMDB_API_KEY": TMDB_API_KEY,
    }
    return [name for name, value in required.items() if not value]