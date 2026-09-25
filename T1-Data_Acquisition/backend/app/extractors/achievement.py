"""extractors/achievement.py -- vision extraction of a general career/technical achievement proof."""

from ..llm import call_vision

PROMPT = """You are reading a document/certificate proving a technical or career
achievement (e.g. a paper acceptance, a competition result, an award). Return
ONLY valid JSON in exactly this shape, no prose:

{
  "title": "...",
  "description": "one short sentence describing the achievement",
  "date": "YYYY-MM-DD or null if not visible"
}

Use null for anything not clearly visible -- never guess.
"""


def extract_achievement(file_bytes: bytes, mime_type: str) -> dict:
    result = call_vision(PROMPT, file_bytes, mime_type)
    for key in ("title", "description", "date"):
        result.setdefault(key, None)
    return result