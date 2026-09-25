"""
extractors/marksheet.py
------------------------
Reads one semester's marksheet (image or PDF, photographed or scanned -- 
whatever the student has) and extracts subject-wise marks + that semester's
SGPA. Uses vision LLM extraction since marksheet layouts vary too much
(different colleges, photos vs. scans) for a fixed regex/OCR-template
approach to hold up.
"""

from ..llm import call_vision

PROMPT = """You are reading a college semester marksheet/grade card image or PDF.
Extract the data and return ONLY valid JSON in exactly this shape, no prose:

{{
  "subjects": [
    {{"code": "...", "name": "...", "credits": 4, "grade": "A", "points": 9}}
  ],
  "sgpa": 8.7
}}

Rules:
- If a field is not visible/present, use null for that field (never invent numbers).
- "points" means grade points for that subject (e.g. O=10, A+=9, A=8 etc, as printed on the card).
- If the card does not show a printed SGPA, compute it as
  sum(credits*points)/sum(credits) across the subjects you extracted, and note "sgpa_computed": true.
- This is semester number {semester_no}.
"""


def extract_marksheet(file_bytes: bytes, mime_type: str, semester_no: int) -> dict:
    result = call_vision(PROMPT.format(semester_no=semester_no), file_bytes, mime_type)
    result["semester"] = semester_no
    result.setdefault("subjects", [])
    result.setdefault("sgpa", None)
    return result