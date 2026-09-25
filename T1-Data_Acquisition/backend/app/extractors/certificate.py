"""extractors/certificate.py -- vision extraction of a certification file (image/PDF)."""

from ..llm import call_vision

PROMPT = """You are reading a certificate/certification badge (image or PDF).
Return ONLY valid JSON in exactly this shape, no prose:

{
  "name": "...",
  "issuer": "...",
  "issued_on": "YYYY-MM-DD or null if not visible"
}

Use null for anything not clearly visible on the certificate -- never guess.
"""


def extract_certificate(file_bytes: bytes, mime_type: str) -> dict:
    result = call_vision(PROMPT, file_bytes, mime_type)
    result.setdefault("name", None)
    result.setdefault("issuer", None)
    result.setdefault("issued_on", None)
    return result