import json
from pathlib import Path

import frontmatter

p = Path(__file__).resolve()

REPO_ROOT = p.parent.parent
POSTINGS_DIR = REPO_ROOT / "evals" / "postings"
LABELS_DIR = REPO_ROOT / "evals" / "labels"
LABELS_DIR.mkdir(exist_ok=True)

labels = {}

for post in sorted(POSTINGS_DIR.glob("*.md")):
    metadata, content = frontmatter.parse(post.read_text(encoding="utf-8"))

    post_content = {
        "company": str(metadata.get("Company", "unknown")).lower(),
        "title": str(metadata.get("Title", "unknown")).lower(),
        "seniority": None,
        "work_mode": None,
        "required_skills": None,
        "gut_score": None,
        "gut_reason": None,
    }

    labels[post.stem] = post_content

with open(LABELS_DIR / "labels.json", "w", encoding="utf-8") as f:
    json.dump(labels, f, indent=2)
