import os
from dotenv import load_dotenv

load_dotenv()

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Scraping Settings
IMAGES_PER_POSITION = int(os.getenv("IMAGES_PER_POSITION", "30"))

DOWNLOAD_DELAY = int(os.getenv("DOWNLOAD_DELAY", "2"))
SEARCH_SUFFIX = os.getenv("SEARCH_SUFFIX", "Single Person Asian")
BASE_DOWNLOAD_DIR = os.path.join(BASE_DIR, os.getenv("BASE_DOWNLOAD_DIR", "downloads"))


# Position file
POSITION_FILE = os.path.join(BASE_DIR, "position.text")

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
