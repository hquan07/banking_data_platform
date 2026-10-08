import json

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from fraud.scoring.train_ds1_isolation import FEATURES, prepare_ds1, train_ds1_candidate


def ds1_frame(rows=300):
    data = {
        "Time": list(range(rows)),
        "Amount": [float((index % 50) + 1) for index in range(rows)],
        "Class": [int(index % 20 == 0) for index in range(rows)],
    }
    for feature_index, name in enumerate(FEATURES, start=1):
        data[name] = [((index * feature_index) % 37) / 10 for index in range(rows)]
    return pd.DataFrame(data)


def test_ds1_candidate_uses_relative_time_holdout_and_writes_artifact(tmp_path):
    source = tmp_path / "creditcard.csv"
    ds1_frame().to_csv(source, index=False)

    metadata = train_ds1_candidate(source, tmp_path / "models", "ds1-test", 0.05)

    assert metadata["dataset_id"] == "ds1_creditcard"
    assert metadata["train_time_max"] < metadata["holdout_time_min"]
    assert metadata["holdout_rows"] == 60
    assert metadata["status"] == "CANDIDATE_NOT_DEPLOYED"
    assert metadata["production_eligible"] is False
    assert set(metadata["feature_schema"]) == set(FEATURES)
    saved = json.loads((tmp_path / "models/ds1-test/metadata.json").read_text())
    assert saved["model_sha256"] == metadata["model_sha256"]


def test_ds1_training_rejects_missing_features_and_overwrite(tmp_path):
    with pytest.raises(ValueError, match="Missing DS1"):
        prepare_ds1(ds1_frame().drop(columns="V28"))
    source = tmp_path / "creditcard.csv"
    ds1_frame().to_csv(source, index=False)
    train_ds1_candidate(source, tmp_path / "models", "ds1-test", 0.05)
    with pytest.raises(FileExistsError):
        train_ds1_candidate(source, tmp_path / "models", "ds1-test", 0.05)
