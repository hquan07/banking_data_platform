"""Offline governance checks; fixtures do not create a deployed model."""

from datetime import datetime, timedelta, timezone

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from fraud.scoring.train_model import prepare_data, train_candidate
from fraud.scoring.demo_dataset import generate_rows, write_demo_csv
from fraud.scoring.demo_registry import select_candidate, rollback
from fraud.scoring.demo_monitor import monitor_demo


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


def test_demo_dataset_is_reproducible_and_never_production_eligible(tmp_path):
    assert generate_rows(300, seed=7) == generate_rows(300, seed=7)
    source = tmp_path / "synthetic.csv"
    write_demo_csv(source, count=300, seed=7)
    metadata = train_candidate(source, tmp_path / "models", "demo-v1", 0.7)
    assert metadata["data_origin"] == "synthetic_demo"
    assert metadata["evaluation_scope"] == "pipeline_test_only"
    assert metadata["production_eligible"] is False
    assert metadata["status"] == "CANDIDATE_NOT_DEPLOYED"
    with pytest.raises(FileExistsError):
        write_demo_csv(source)


def test_demo_selection_monitoring_and_threshold_rollback(tmp_path):
    source = tmp_path / "synthetic.csv"
    write_demo_csv(source, count=300, seed=7)
    root = tmp_path / "candidates"
    train_candidate(source, root, "demo-v1", 0.7)
    select_candidate(root, "demo-v1", 0.7)
    select_candidate(root, "demo-v1", 0.8)
    monitor_source = tmp_path / "later.csv"
    write_demo_csv(monitor_source, count=300, seed=8,
                   start=datetime(2026, 2, 1, tzinfo=timezone.utc))
    result = monitor_demo(root, monitor_source)
    assert result["scope"] == "synthetic_demo_only"
    assert result["performance"]["pr_auc"] >= 0
    assert set(result["mean_shift_in_train_std"]) == {
        "amount", "hour_of_day", "velocity_1h", "diff_from_avg", "is_international"
    }
    assert rollback(root)["active"]["threshold"] == 0.7
