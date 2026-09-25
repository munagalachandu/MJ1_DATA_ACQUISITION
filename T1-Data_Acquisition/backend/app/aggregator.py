"""
aggregator.py
--------------
Combines every extractor's output into the one unified profile JSON
(schema v1.1 -- see shared_json_contract from the earlier planning doc).
The only computed value here is CGPA, and only as a straightforward
credit-weighted average of the SGPAs that were actually extracted --
no skill-confidence weighting happens anywhere in this file, per this
stage's brief: acquisition and extraction only.
"""

from datetime import datetime, timezone


def compute_cgpa(semesters: list[dict]) -> float | None:
    valid = [s for s in semesters if s.get("sgpa") is not None]
    if not valid:
        return None

    total_credits = 0
    total_points = 0.0
    for s in valid:
        credits = sum((sub.get("credits") or 0) for sub in s.get("subjects", []))
        if credits > 0:
            total_credits += credits
            total_points += credits * s["sgpa"]

    if total_credits > 0:
        return round(total_points / total_credits, 2)
    # Fall back to a plain average when credit info wasn't extractable.
    return round(sum(s["sgpa"] for s in valid) / len(valid), 2)


def build_profile(
    *,
    name: str,
    degree: str,
    specialization: str,
    semesters: list[dict],
    resume_data: dict | None,
    github_data: dict | None,
    leetcode_data: dict | None,
    other_platforms: list[dict],
    certifications: list[dict],
    hackathons: list[dict],
    achievements: list[dict],
    sources_log: list[dict],
) -> dict:
    skills = []
    projects = []
    certifications_out = list(certifications)

    if resume_data:
        for s in resume_data.get("skills", []):
            skills.append({"skill": s, "source": "resume"})
        for p in resume_data.get("projects", []):
            projects.append({**p, "source": "resume"})
        for c in resume_data.get("certifications", []):
            certifications_out.append({**c, "source": "resume"})

    coding_stats = []
    if github_data:
        coding_stats.append({
            "platform": "github", "handle": github_data["handle"],
            "metrics": {k: v for k, v in github_data.items() if k not in ("handle", "projects")},
        })
        for lang in github_data.get("languages", []):
            skills.append({"skill": lang, "source": "github"})
        for p in github_data.get("projects", []):
            projects.append({**p, "source": "github"})

    if leetcode_data:
        coding_stats.append({
            "platform": "leetcode", "handle": leetcode_data["handle"],
            "metrics": {k: v for k, v in leetcode_data.items() if k != "handle"},
        })
        if leetcode_data.get("total_solved"):
            skills.append({"skill": "Data Structures & Algorithms", "source": "leetcode"})

    for op in other_platforms:
        coding_stats.append({
            "platform": op.get("platform", "unknown"),
            "handle": op.get("handle", ""),
            "metrics": {"note": "manually entered, not auto-verified"},
        })

    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "degree": degree,
        "specialization": specialization,
        "sources": sources_log,
        "academics": {
            "semesters": semesters,
            "cgpa": compute_cgpa(semesters),
        },
        "skills": skills,
        "projects": projects,
        "certifications": certifications_out,
        "hackathons": hackathons,
        "achievements": achievements,
        "coding_stats": coding_stats,
    }