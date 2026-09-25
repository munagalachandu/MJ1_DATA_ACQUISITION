"""extractors/hackathon.py -- vision extraction of a hackathon certificate/proof file."""

from ..llm import call_vision

PROMPT = """You are reading a hackathon participation/winning certificate or proof
document (image or PDF). Return ONLY valid JSON in exactly this shape, no prose:

{
  "name": "name of the hackathon/event",
  "position": "e.g. Winner / Runner-up / Participant, or null if not stated",
  "organizer": "...",
  "date": "YYYY-MM-DD or null if not visible"
}

Use null for anything not clearly visible -- never guess.
"""


def extract_hackathon(file_bytes: bytes, mime_type: str) -> dict:
    result = call_vision(PROMPT, file_bytes, mime_type)
    for key in ("name", "position", "organizer", "date"):
        result.setdefault(key, None)
    return result