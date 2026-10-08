"""Offline governance checks; fixtures do not create a deployed model."""

from datetime import datetime, timedelta, timezone

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from fraud.scoring.train_model import prepare_data, train_candidate


def labeled_frame():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return pd.DataFrame({
        "event_time": [start + timedelta(minutes=i) for i in range(300)],
        "amount": [float(100 + i) for i in range(300)],
        "hour_of_day": [i % 24 for i in range(300)],
        "velocity_1h": [i % 7 for i in range(300)],
        "diff_from_avg": [1.0 + i / 300 for i in range(300)],
        "is_international": [i % 2 for i in range(300)],
        "is_fraud": [int(i % 10 == 0) for i in range(300)],
    })


def test_candidate_uses_temporal_holdout_and_writes_metadata(tmp_path):
    source = tmp_path / "labeled.csv"
    labeled_frame().to_csv(source, index=False)
    metadata = train_candidate(source, tmp_path / "models", "test-v1", 0.7)
    assert metadata["status"] == "CANDIDATE_NOT_DEPLOYED"
    assert metadata["holdout_rows"] == 60
    assert metadata["train_end_utc"] < metadata["holdout_start_utc"]
    assert 0 <= metadata["metrics"]["pr_auc"] <= 1
    assert (tmp_path / "models/test-v1/metadata.json").exists()
    with pytest.raises(FileExistsError):
        train_candidate(source, tmp_path / "models", "test-v1", 0.7)


def test_refuses_overlapping_periods_and_unlabeled_data():
    frame = labeled_frame()
    frame.loc[240, "event_time"] = frame.loc[239, "event_time"]
    with pytest.raises(ValueError, match="overlap"):
        prepare_data(frame)
    with pytest.raises(ValueError, match="Missing"):
        prepare_data(labeled_frame().drop(columns="is_fraud"))
