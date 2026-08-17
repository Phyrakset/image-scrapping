import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Scraper Settings
DEFAULT_IMAGES_PER_POSITION = 40
IMAGES_PER_POSITION = int(os.environ.get("IMAGES_PER_POSITION", DEFAULT_IMAGES_PER_POSITION))
DEFAULT_SEARCH_SUFFIX = "Single Person Asian"
SEARCH_SUFFIX = os.environ.get("SEARCH_SUFFIX", DEFAULT_SEARCH_SUFFIX)
DOWNLOAD_DELAY = int(os.environ.get("DOWNLOAD_DELAY", "2"))
BASE_DOWNLOAD_DIR = os.environ.get("BASE_DOWNLOAD_DIR", "downloads")
POSITION_FILE = os.environ.get("POSITION_FILE", "position.text")
ONLY_AI_PERSON = os.environ.get("ONLY_AI_PERSON", "false").lower() in ("true", "1", "yes")

# AI API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LOCAL_SD_URL = os.environ.get("LOCAL_SD_URL", "http://127.0.0.1:7860")

# OpenRouter Profiles & API Keys (Loaded securely from .env)
OPENROUTER_PROFILES = {
    "sophy_coder": {
        "name": "👤 Sophy Coder",
        "key": os.environ.get("OPENROUTER_KEY_SOPHY_CODER", ""),
    },
    "aht50712": {
        "name": "👤 aht50712@gmail.com",
        "key": os.environ.get("OPENROUTER_KEY_AHT50712", ""),
    },
    "asp25035": {
        "name": "👤 asp25035@gmail.com",
        "key": os.environ.get("OPENROUTER_KEY_ASP25035", ""),
    },
    "openrouter_default": {
        "name": "👤 openrouter (Primary)",
        "key": os.environ.get("OPENROUTER_KEY_DEFAULT", ""),
    },
    "sophyset2016": {
        "name": "👤 sophyset2016@gmail.com",
        "key": os.environ.get("OPENROUTER_KEY_SOPHYSET2016", ""),
    },
}

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", OPENROUTER_PROFILES["sophy_coder"]["key"])
