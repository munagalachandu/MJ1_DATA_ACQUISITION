"""
config.py
---------
All environment-driven settings in one place. Set these on Render's
dashboard (Environment tab) for the backend service:

  GEMINI_API_KEY   - required, primary LLM (text + vision)
  GROQ_API_KEY     - optional, free-tier fallback LLM (text + vision)
  GITHUB_TOKEN     - optional but recommended, raises GitHub API rate limit
  ALLOWED_ORIGINS  - comma-separated list, e.g. https://your-frontend.onrender.com
                     (only needed for your DEPLOYED frontend -- any
                     localhost/127.0.0.1 origin is always allowed locally,
                     on any port, via LOCAL_ORIGIN_REGEX below, so you don't
                     need to guess which port your dev server picked)
"""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

_env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()]

LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "meta-llama/llama-4-scout-17b-16e-instruct"
)