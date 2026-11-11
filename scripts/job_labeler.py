# This script should parse the .md files in /evals/postings/, and then populate labels.json with info from each posting.
#
# Notes:
#
# if labels.json exists, check number of listings. if less than 20, add new listings. if more than 20, then create a new 00-labels.json file that increments 01, 02, etc., and then add new listings. otherwise create labels.json and then add listings up to 20.
#
# pathlib.Path("evals/postings").glob("*.md") gives you the files, and .stem gives you the filename without the extension.
# json.dumps(..., indent=2) makes the output readable, so editing it by hand is pleasant.
# Sort the keys so the order matches your file numbering.
# Use full, standard skill names (“JavaScript”, not “JS”). They’ll line up with your SkillAlias table later.
# Only list must-have skills under required_skills, 5–10 per posting. A “preferred” or “bonus” skill doesn’t count.
# Write gut_score and gut_reason last, after the other fields, so your score comes from what you actually wrote down and not from first impressions.
# Mark anything you’re unsure of. If a posting doesn’t say whether it’s remote, label it "unknown". That’s the same rule you’re giving the model.
#
#

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
