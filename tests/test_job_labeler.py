import json

from job_labeler import load_labels


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
