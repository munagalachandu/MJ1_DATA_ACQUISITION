"""
llm.py
------
One narrow job: send a prompt (optionally with an image/PDF attached) to an
LLM and get JSON back. Gemini is tried first (you have a key); if it's
missing, rate-limited, or errors out, Groq is tried as the free-tier
fallback. Plain `requests` calls to each provider's REST API are used on
purpose instead of their SDKs -- fewer dependencies, fewer version-mismatch
surprises when deploying to Render.

Every extractor in extractors/ calls call_text() or call_vision() and gets
back a plain Python dict -- they never need to know which provider actually
answered.
"""

from __future__ import annotations
import base64
import io
import json
import re
import requests

from . import config

try:
    import fitz  # PyMuPDF -- already a dependency, used by extractors/resume.py
except ImportError:  # pragma: no cover
    fitz = None

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(Exception):
    pass


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _parse_json(text: str) -> dict:
    cleaned = _strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: grab the first {...} block in the response.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise LLMError(f"Could not parse JSON from LLM response: {text[:300]}")


# ---------------------------------------------------------------- Gemini --
def _gemini_text(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{config.GEMINI_MODEL}:generateContent"
    )

    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    r = requests.post(
        url,
        headers=headers,
        json=body,
        timeout=60,
    )

    if not r.ok:
        raise LLMError(
            f"Gemini HTTP {r.status_code}: {r.text[:2000]}"
        )

    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _gemini_vision(prompt: str, file_bytes: bytes, mime_type: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{config.GEMINI_MODEL}:generateContent"
    )

    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    b64 = base64.b64encode(file_bytes).decode("utf-8")

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64,
                        }
                    },
                ]
            }
        ]
    }

    r = requests.post(
        url,
        headers=headers,
        json=body,
        timeout=60,
    )

    if not r.ok:
        raise LLMError(
            f"Gemini HTTP {r.status_code}: {r.text[:2000]}"
        )

    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
# ------------------------------------------------------------------ Groq --
def _groq_text(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    body = {"model": config.GROQ_TEXT_MODEL, "messages": [{"role": "user", "content": prompt}]}
    r = requests.post(GROQ_URL, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _groq_vision(prompt: str, file_bytes: bytes, mime_type: str) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    body = {
        "model": config.GROQ_VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ],
        }],
    }
    r = requests.post(GROQ_URL, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ------------------------------------------------------------- Public API --
def call_text(prompt: str) -> dict:
    """Text-only prompt -> parsed JSON dict. Gemini first, Groq fallback."""
    errors = []
    if config.GEMINI_API_KEY:
        try:
            return _parse_json(_gemini_text(prompt))
        except Exception as e:
            errors.append(f"gemini: {e}")
    if config.GROQ_API_KEY:
        try:
            return _parse_json(_groq_text(prompt))
        except Exception as e:
            errors.append(f"groq: {e}")
    raise LLMError(f"All text LLM providers failed: {'; '.join(errors) or 'no API key configured'}")


def _pdf_first_page_to_png(file_bytes: bytes) -> bytes:
    """Rasterize a PDF's first page to a PNG so a Groq vision fallback can
    read it. Groq's vision model only accepts images, never PDFs -- so
    without this step a PDF marksheet/certificate simply fails whenever
    Gemini is unavailable (missing/invalid key, rate-limited, quota, etc).
    Raises LLMError if PyMuPDF isn't installed or the PDF can't be opened.
    """
    if fitz is None:
        raise LLMError("PyMuPDF (fitz) is not installed; cannot rasterize PDF for Groq fallback")
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise LLMError("PDF has no pages")
    # zoom for a sharper render -- vision models read blurry scans poorly
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
    return pix.tobytes("png")


def call_vision(prompt: str, file_bytes: bytes, mime_type: str) -> dict:
    """Prompt + image/PDF -> parsed JSON dict. Gemini first, Groq fallback.

    PDFs work directly with Gemini's inline_data. Groq's vision model only
    accepts images, so when Gemini fails (or has no key) and the file is a
    PDF, its first page is rasterized to a PNG before handing it to Groq.
    """
    errors = []
    if config.GEMINI_API_KEY:
        try:
            return _parse_json(_gemini_vision(prompt, file_bytes, mime_type))
        except Exception as e:
            errors.append(f"gemini: {e}")

    if config.GROQ_API_KEY:
        try:
            if mime_type.startswith("image/"):
                return _parse_json(_groq_vision(prompt, file_bytes, mime_type))
            elif mime_type == "application/pdf":
                png_bytes = _pdf_first_page_to_png(file_bytes)
                return _parse_json(_groq_vision(prompt, png_bytes, "image/png"))
            else:
                errors.append(f"groq: unsupported mime type {mime_type!r} for vision fallback")
        except Exception as e:
            errors.append(f"groq: {e}")

    raise LLMError(f"All vision LLM providers failed: {'; '.join(errors) or 'no API key configured'}")