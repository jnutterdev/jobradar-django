import json

from job_labeler import load_labels, update_labels, write_labels

JUDGMENT_FIELDS = ["seniority", "work_mode", "required_skills", "gut_score", "gut_reason"]


def test_load_labels_missing_file(tmp_path):
    path = tmp_path / "labels.json"
    result = load_labels(path)

    assert result == {}


def test_load_labels_existing_file(tmp_path):
    mock_post = {"01-test": {"company": "weyland-yutani"}}
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(mock_post), encoding="utf-8")
    result = load_labels(path)

    assert result == mock_post


def test_update_labels_new_posting(tmp_path):
    (tmp_path / "02-test.md").write_text(
        """---
Title: Blade Runner
Company: Tyrell Corporation
---

Posting body.
""",
        encoding="utf-8",
    )

    result = update_labels({}, tmp_path)

    entry = result["02-test"]
    assert entry["company"] == "tyrell corporation"
    assert entry["title"] == "blade runner"
    for field in JUDGMENT_FIELDS:
        assert entry[field] is None


def test_update_labels_skips_existing_posting(tmp_path):
    (tmp_path / "01-test.md").write_text(
        """---
Title: Something Else
Company: Other Co
---
""",
        encoding="utf-8",
    )
    existing = {"01-test": {"company": "weyland-yutani", "gut_score": 90}}

    result = update_labels(existing, tmp_path)

    assert result["01-test"] == {"company": "weyland-yutani", "gut_score": 90}


def test_update_labels_missing_frontmatter_keys(tmp_path):
    (tmp_path / "03-test.md").write_text(
        """---
Source: linkedin
---
""",
        encoding="utf-8",
    )

    result = update_labels({}, tmp_path)

    assert result["03-test"]["company"] == "unknown"
    assert result["03-test"]["title"] == "unknown"


def test_update_labels_ignores_non_markdown_files(tmp_path):
    (tmp_path / "notes.txt").write_text("not a posting", encoding="utf-8")

    result = update_labels({}, tmp_path)

    assert result == {}


def test_write_labels_creates_folder_and_round_trips(tmp_path):
    labels = {"01-test": {"company": "weyland-yutani", "gut_score": None}}
    path = tmp_path / "labels" / "labels.json"

    write_labels(labels, path)

    assert path.is_file()
    assert load_labels(path) == labels
