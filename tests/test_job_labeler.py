from job_labeler import load_labels


def test_load_labels_missing_file(tmp_path):
    path = tmp_path / "labels.json"

    result = load_labels(path)

    assert result == {}
