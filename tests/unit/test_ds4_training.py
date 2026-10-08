import json

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from datasets.schema_mapping import DS4_FEATURES
from fraud.scoring.train_ds4_baf import prepare_ds4, train_ds4_candidate


def ds4_frame(rows=800):
    categorical = {
        "payment_type": ("AA", "AB"),
        "employment_status": ("CA", "CB"),
        "housing_status": ("BA", "BB"),
        "source": ("INTERNET", "TELEAPP"),
        "device_os": ("windows", "linux"),
    }
    data = {
        "fraud_bool": [int((index // 8) % 20 == 0) for index in range(rows)],
        "month": [index % 8 for index in range(rows)],
    }
    for feature_index, name in enumerate(DS4_FEATURES, start=1):
        if name in categorical:
            values = categorical[name]
            data[name] = [values[index % len(values)] for index in range(rows)]
        else:
            data[name] = [float((index * feature_index) % 101) for index in range(rows)]
    return pd.DataFrame(data)


def test_ds4_candidate_uses_month_holdouts_and_writes_artifact(tmp_path):
    source = tmp_path / "Base.csv"
    ds4_frame().to_csv(source, index=False)

    metadata = train_ds4_candidate(source, tmp_path / "models", "ds4-test", 10)

    assert metadata["dataset_id"] == "ds4_baf"
    assert metadata["train_months"] == [0, 1, 2, 3, 4, 5]
    assert metadata["validation_month"] == 6
    assert metadata["holdout_month"] == 7
    assert metadata["status"] == "CANDIDATE_NOT_DEPLOYED"
    assert metadata["production_eligible"] is False
    assert set(metadata["feature_schema"]) == set(DS4_FEATURES)
    saved = json.loads((tmp_path / "models/ds4-test/metadata.json").read_text())
    assert saved["model_sha256"] == metadata["model_sha256"]


def test_ds4_training_rejects_invalid_schema_and_overwrite(tmp_path):
    with pytest.raises(ValueError, match="Missing DS4"):
        prepare_ds4(ds4_frame().drop(columns="velocity_6h"))
    source = tmp_path / "Base.csv"
    ds4_frame().to_csv(source, index=False)
    train_ds4_candidate(source, tmp_path / "models", "ds4-test", 10)
    with pytest.raises(FileExistsError):
        train_ds4_candidate(source, tmp_path / "models", "ds4-test", 10)
