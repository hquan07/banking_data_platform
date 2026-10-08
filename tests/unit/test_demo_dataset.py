"""Synthetic labels are deterministic and explicitly marked as demo data."""

import csv

import pytest

from fraud.scoring.demo_dataset import generate_rows, write_demo_csv


def test_demo_rows_are_reproducible_with_both_labels_in_temporal_periods():
    rows = generate_rows(300, seed=7)
    assert rows == generate_rows(300, seed=7)
    assert rows != generate_rows(300, seed=8)
    assert len(rows) == 300
    assert all(row["data_origin"] == "synthetic_demo" for row in rows)
    assert {row["is_fraud"] for row in rows[:240]} == {0, 1}
    assert {row["is_fraud"] for row in rows[240:]} == {0, 1}


def test_csv_is_created_once(tmp_path):
    path = tmp_path / "demo.csv"
    write_demo_csv(path, 300, 7)
    with path.open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 300
    with pytest.raises(FileExistsError):
        write_demo_csv(path, 300, 7)


def test_rejects_too_few_rows():
    with pytest.raises(ValueError, match="200"):
        generate_rows(199)
