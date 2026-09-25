"""
extractors/github.py
----------------------
Pure GitHub REST API calls -- no LLM needed here, the API already returns
structured data. Set GITHUB_TOKEN in the environment to avoid the very low
unauthenticated rate limit (60 req/hr).
"""

import requests
from .. import config
from ..normalizer import normalize_skill

API_BASE = "https://api.github.com"


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def extract_github(username: str) -> dict:
    profile_r = requests.get(f"{API_BASE}/users/{username}", headers=_headers(), timeout=15)
    profile_r.raise_for_status()
    profile = profile_r.json()

    repos_r = requests.get(
        f"{API_BASE}/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
        headers=_headers(), timeout=15,
    )
    repos_r.raise_for_status()
    repos = repos_r.json()

    languages: dict[str, int] = {}
    projects = []
    for repo in repos:
        lang = repo.get("language")
        if lang:
            canon = normalize_skill(lang)
            languages[canon] = languages.get(canon, 0) + 1
        if not repo.get("fork") and (repo.get("stargazers_count", 0) > 0 or repo.get("size", 0) > 50):
            projects.append({
                "name": repo["name"],
                "description": repo.get("description") or "",
                "skills_used": [normalize_skill(lang)] if lang else [],
                "url": repo.get("html_url"),
            })

    return {
        "handle": username,
        "public_repos": profile.get("public_repos"),
        "followers": profile.get("followers"),
        "languages": sorted(languages, key=languages.get, reverse=True),
        "projects": projects,
        "profile_url": profile.get("html_url"),
    }