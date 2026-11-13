import json
from pathlib import Path
from typing import Any

import frontmatter

p = Path(__file__).resolve()

Labels = dict[str, dict[str, Any]]
REPO_ROOT = p.parent.parent
POSTINGS_DIR = REPO_ROOT / "evals" / "postings"
LABELS_DIR = REPO_ROOT / "evals" / "labels"
LABELS_FILE = LABELS_DIR / "labels.json"


def load_labels(labels_path: Path) -> dict[str, Labels]:
    if labels_path.exists():
        with open(labels_path, "r", encoding="utf-8") as f:
            labels = json.load(f)
    else:
        labels = {}

    return labels


def update_labels(labels: dict, posts_dir: Path) -> dict[str, Labels]:
    for post in sorted(posts_dir.glob("*.md")):
        if post.stem in labels:
            continue

        metadata, _ = frontmatter.parse(post.read_text(encoding="utf-8"))

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

    return labels


def write_labels(labels: dict, labels_file: Path) -> None:
    labels_file.parent.mkdir(exist_ok=True)

    with open(labels_file, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)


def main() -> None:
    labels = load_labels(LABELS_FILE)
    labels = update_labels(labels, POSTINGS_DIR)
    write_labels(labels, LABELS_FILE)


if __name__ == "__main__":
    main()
