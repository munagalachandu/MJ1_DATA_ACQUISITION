"""
extractors/resume.py
---------------------
Pulls text out of a PDF/DOCX resume, then asks the LLM to structure it into
skills / projects / certifications / internships. Text-only call (cheaper
and more reliable than vision for a text-native document like a resume).
"""

import io
import fitz          # PyMuPDF
import docx          # python-docx

from ..llm import call_text, call_vision
from ..normalizer import normalize_skill

PROMPT = """You are extracting structured data from a student's resume for a
placement-preparation system. Return ONLY valid JSON, no prose, in exactly this shape:

{{
  "skills": ["skill1", "skill2"],
  "projects": [{{"name": "...", "description": "...", "skills_used": ["..."]}}],
  "certifications": [{{"name": "...", "issuer": "..."}}],
  "internships": [{{"role": "...", "company": "...", "skills_used": ["..."]}}]
}}

If a section is absent from the resume, return an empty list for it -- never invent entries.

Resume text:
---
{resume_text}
---
"""

# Used when a PDF has no extractable text layer (a scanned photo/print of a
# resume rather than an exported/typed PDF). Same shape as PROMPT above,
# just fed the page image instead of extracted text.
VISION_PROMPT = """You are reading an image of a student's resume for a
placement-preparation system. Return ONLY valid JSON, no prose, in exactly this shape:

{
  "skills": ["skill1", "skill2"],
  "projects": [{"name": "...", "description": "...", "skills_used": ["..."]}],
  "certifications": [{"name": "...", "issuer": "..."}],
  "internships": [{"role": "...", "company": "...", "skills_used": ["..."]}]
}

If a section is absent from the resume, return an empty list for it -- never invent entries.
"""

# A resume with real, extractable text almost always has well over this many
# characters. Anything shorter is treated as a scanned/no-text-layer PDF
# (e.g. a photo of a printed resume) and routed to vision extraction instead
# of silently sending the LLM an (almost) empty prompt.
MIN_TEXT_LENGTH = 40


def _extract_text(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    elif ext in ("docx", "doc"):
        d = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in d.paragraphs)
    raise ValueError(f"Unsupported resume format: .{ext}")


def _first_page_png(file_bytes: bytes) -> bytes:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
    return pix.tobytes("png")


def extract_resume(file_bytes: bytes, filename: str) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1]
    text = _extract_text(file_bytes, filename)

    if len(text.strip()) < MIN_TEXT_LENGTH and ext == "pdf":
        # No usable text layer -- almost certainly a scanned/photographed
        # resume. Rasterize the first page and read it with vision instead
        # of extracting structure from near-empty text.
        structured = call_vision(VISION_PROMPT, _first_page_png(file_bytes), "image/png")
    else:
        structured = call_text(PROMPT.format(resume_text=text[:12000]))

    skills = [normalize_skill(s) for s in structured.get("skills", [])]
    for p in structured.get("projects", []):
        p["skills_used"] = [normalize_skill(s) for s in p.get("skills_used", [])]
        skills += p["skills_used"]
    for i in structured.get("internships", []):
        i["skills_used"] = [normalize_skill(s) for s in i.get("skills_used", [])]
        skills += i["skills_used"]

    structured["skills"] = sorted(set(skills))
    return structured