"""
extractors/leetcode.py
------------------------
LeetCode has no official public API. This uses the same unauthenticated
GraphQL endpoint the LeetCode website itself calls -- no key needed, but
it's an unofficial surface, so it may need small fixes if LeetCode changes
their schema.
"""

import requests

GRAPHQL_URL = "https://leetcode.com/graphql"

QUERY = """
query userStats($username: String!) {
  matchedUser(username: $username) {
    username
    submitStats: submitStatsGlobal { acSubmissionNum { difficulty count } }
    profile { ranking reputation }
  }
  userContestRanking(username: $username) { rating globalRanking topPercentage }
}
"""


def extract_leetcode(username: str) -> dict:
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": {"username": username}},
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    user = data.get("matchedUser") or {}
    contest = data.get("userContestRanking") or {}
    counts = {row["difficulty"]: row["count"] for row in user.get("submitStats", {}).get("acSubmissionNum", [])}

    return {
        "handle": username,
        "total_solved": counts.get("All", 0),
        "easy": counts.get("Easy", 0),
        "medium": counts.get("Medium", 0),
        "hard": counts.get("Hard", 0),
        "ranking": (user.get("profile") or {}).get("ranking"),
        "contest_rating": contest.get("rating"),
        "global_ranking": contest.get("globalRanking"),
    }