"""
normalizer.py
-------------
Only job at this stage: collapse skill-name variants ("ReactJS" / "React.js"
/ "React") into one canonical name, so the Knowledge Graph in the next task
doesn't end up with duplicate nodes for the same skill.

Deliberately does NOT assign confidence/weight scores. This stage is pure
data extraction and acquisition -- deciding how much to trust each source
is a Stage-2 reasoning concern, not something to bake into the raw profile.
"""

import difflib

CANONICAL_SKILLS: dict[str, str] = {
    "reactjs": "React", "react.js": "React", "react": "React",
    "node": "Node.js", "nodejs": "Node.js", "node.js": "Node.js",
    "py": "Python", "python3": "Python", "python": "Python",
    "js": "JavaScript", "javascript": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "sklearn": "Scikit-learn", "scikit-learn": "Scikit-learn",
    "dsa": "Data Structures & Algorithms",
    "data structures and algorithms": "Data Structures & Algorithms",
    "oop": "Object-Oriented Programming",
    "dp": "Dynamic Programming", "dynamic programming": "Dynamic Programming",
    "ml": "Machine Learning", "machine learning": "Machine Learning",
    "dl": "Deep Learning", "deep learning": "Deep Learning",
    "nlp": "Natural Language Processing",
    "aws": "AWS", "amazon web services": "AWS",
    "docker": "Docker", "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "git": "Git", "github": "Git",
    "sql": "SQL",
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
}


def normalize_skill(raw: str) -> str:
    if not raw:
        return raw
    key = raw.strip().lower()
    if key in CANONICAL_SKILLS:
        return CANONICAL_SKILLS[key]

    candidates = list(set(CANONICAL_SKILLS.values()))
    match = difflib.get_close_matches(raw.strip(), candidates, n=1, cutoff=0.85)
    if match:
        return match[0]

    return raw.strip()