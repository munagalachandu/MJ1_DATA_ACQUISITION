"""
main.py
--------
Single-endpoint backend: the frontend collects everything across all its
tabs into one FormData object and POSTs it once to /api/submit. The backend
runs every extractor, aggregates the results into the unified profile JSON,
and returns it in one response -- matching the "fill everything, click
Submit once, see the extracted profile" flow the UI is built around.

Run locally:
    uvicorn app.main:app --reload --port 8000

Deploy on Render as a Web Service with start command:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import json
import mimetypes
from typing import List, Optional

from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .aggregator import build_profile
from .extractors.marksheet import extract_marksheet
from .extractors.resume import extract_resume
from .extractors.github import extract_github
from .extractors.leetcode import extract_leetcode
from .extractors.certificate import extract_certificate
from .extractors.hackathon import extract_hackathon
from .extractors.achievement import extract_achievement

app = FastAPI(title="Placement Prep - Data Acquisition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_origin_regex=config.LOCAL_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/api/health")
def health():
    return {"status": "ok"}


def _log(sources: list, name: str, status: str, message: str = ""):
    entry = {"source": name, "status": status}
    if message:
        entry["message"] = message
    sources.append(entry)


async def _read(file: UploadFile) -> bytes:
    return await file.read()


# Browsers usually set UploadFile.content_type correctly, but it's not
# guaranteed (some pickers/drag-drop flows send "" or
# "application/octet-stream"). The old fallback of always defaulting to
# "image/jpeg" silently mislabels every PDF that arrives without a proper
# content-type -- Gemini then gets a PDF's bytes tagged as a JPEG and the
# vision call fails or returns garbage. Guess from the filename extension
# instead, and only fall back to image/jpeg as an absolute last resort.
_GENERIC_TYPES = {"", "application/octet-stream", "binary/octet-stream"}


def _guess_mime(file: UploadFile) -> str:
    declared = (file.content_type or "").lower()
    if declared and declared not in _GENERIC_TYPES:
        return declared

    guessed, _ = mimetypes.guess_type(file.filename or "")
    if guessed:
        return guessed

    return "image/jpeg"


def _parse_json_list(raw: str) -> list:
    try:
        parsed = json.loads(raw) if raw else []
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


@app.post("/api/submit")
async def submit(
    name: str = Form(...),
    degree: str = Form(...),
    specialization: str = Form(""),
    semester_numbers: List[int] = Form(default=[]),
    semester_files: List[UploadFile] = File(default=[]),
    resume_file: Optional[UploadFile] = File(default=None),
    github_username: str = Form(""),
    leetcode_username: str = Form(""),
    other_platforms_json: str = Form("[]"),
    certification_files: List[UploadFile] = File(default=[]),
    certifications_manual_json: str = Form("[]"),
    hackathon_files: List[UploadFile] = File(default=[]),
    hackathons_manual_json: str = Form("[]"),
    achievement_files: List[UploadFile] = File(default=[]),
    achievements_manual_json: str = Form("[]"),
):
    sources_log: list = []

    # ---- Semester marksheets ----
    semesters = []
    for num, f in zip(semester_numbers, semester_files):
        try:
            data = extract_marksheet(await _read(f), _guess_mime(f), num)
            semesters.append(data)
            _log(sources_log, f"semester_{num}", "ok")
        except Exception as e:
            _log(sources_log, f"semester_{num}", "error", str(e))

    # ---- Resume ----
    resume_data = None
    if resume_file is not None and resume_file.filename:
        try:
            resume_data = extract_resume(await _read(resume_file), resume_file.filename)
            _log(sources_log, "resume", "ok")
        except Exception as e:
            _log(sources_log, "resume", "error", str(e))
    else:
        _log(sources_log, "resume", "skipped", "no file provided")

    # ---- GitHub ----
    github_data = None
    if github_username.strip():
        try:
            github_data = extract_github(github_username.strip())
            _log(sources_log, "github", "ok")
        except Exception as e:
            _log(sources_log, "github", "error", str(e))
    else:
        _log(sources_log, "github", "skipped", "no username provided")

    # ---- LeetCode ----
    leetcode_data = None
    if leetcode_username.strip():
        try:
            leetcode_data = extract_leetcode(leetcode_username.strip())
            _log(sources_log, "leetcode", "ok")
        except Exception as e:
            _log(sources_log, "leetcode", "error", str(e))
    else:
        _log(sources_log, "leetcode", "skipped", "no username provided")

    # ---- Other coding profiles (manual entries, no automated extractor yet) ----
    other_platforms = _parse_json_list(other_platforms_json)
    for op in other_platforms:
        _log(sources_log, op.get("platform", "other"), "ok", "manual entry, not auto-verified")

    # ---- Certifications: uploaded files (auto-extracted) + manual entries ----
    certifications = []
    for f in certification_files:
        try:
            cert = extract_certificate(await _read(f), _guess_mime(f))
            certifications.append({**cert, "source": "certificate_upload"})
            _log(sources_log, f"certificate:{f.filename}", "ok")
        except Exception as e:
            _log(sources_log, f"certificate:{f.filename}", "error", str(e))
    for manual in _parse_json_list(certifications_manual_json):
        certifications.append({**manual, "source": "manual_entry"})
        _log(sources_log, f"certificate_manual:{manual.get('name','untitled')}", "ok")

    # ---- Hackathons: uploaded files (auto-extracted) + manual entries ----
    hackathons = []
    for f in hackathon_files:
        try:
            hack = extract_hackathon(await _read(f), _guess_mime(f))
            hackathons.append({**hack, "source": "hackathon_upload"})
            _log(sources_log, f"hackathon:{f.filename}", "ok")
        except Exception as e:
            _log(sources_log, f"hackathon:{f.filename}", "error", str(e))
    for manual in _parse_json_list(hackathons_manual_json):
        hackathons.append({**manual, "source": "manual_entry"})
        _log(sources_log, f"hackathon_manual:{manual.get('name','untitled')}", "ok")

    # ---- Achievements: uploaded files (auto-extracted) + manual entries ----
    achievements = []
    for f in achievement_files:
        try:
            ach = extract_achievement(await _read(f), _guess_mime(f))
            achievements.append({**ach, "source": "achievement_upload"})
            _log(sources_log, f"achievement:{f.filename}", "ok")
        except Exception as e:
            _log(sources_log, f"achievement:{f.filename}", "error", str(e))
    for manual in _parse_json_list(achievements_manual_json):
        achievements.append({**manual, "source": "manual_entry"})
        _log(sources_log, f"achievement_manual:{manual.get('title','untitled')}", "ok")

    profile = build_profile(
        name=name,
        degree=degree,
        specialization=specialization,
        semesters=semesters,
        resume_data=resume_data,
        github_data=github_data,
        leetcode_data=leetcode_data,
        other_platforms=other_platforms,
        certifications=certifications,
        hackathons=hackathons,
        achievements=achievements,
        sources_log=sources_log,
    )
    return profile