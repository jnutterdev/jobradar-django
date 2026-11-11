from pathlib import Path

import frontmatter

p = Path(__file__).resolve()

REPO_ROOT = p.parent.parent
POSTINGS_DIR = REPO_ROOT / "evals" / "postings"
LABELS_DIR = REPO_ROOT / "evals" / "labels"

for post in sorted(POSTINGS_DIR.glob("*.md")):
    print(post.stem)

    metadata, content = frontmatter.parse(post.read_text(encoding="utf-8"))
    print(metadata.get("Company", "unknown"))


LABELS_DIR.mkdir(exist_ok=True)
