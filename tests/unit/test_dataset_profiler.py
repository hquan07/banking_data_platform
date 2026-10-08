import json

import pandas as pd

from datasets.profile_datasets import profile_csv, profile_dataset


def test_profile_csv_reports_quality_and_checksum(tmp_path):
    source = tmp_path / "events.csv"
    pd.DataFrame({
        "amount": [10.0, 20.5, None],
        "kind": ["PAYMENT", "TRANSFER", "PAYMENT"],
    }).to_csv(source, index=False)

    result = profile_csv(
        source,
        required_columns=["amount", "kind", "label"],
        minimum_rows=3,
        chunk_size=2,
    )

    assert result["row_count"] == 3
    assert result["missing_required_columns"] == ["label"]
    assert result["valid"] is False
    amount = next(column for column in result["columns"] if column["name"] == "amount")
    assert amount["missing_count"] == 1
    assert amount["numeric_mean"] == 15.25
    assert len(result["sha256"]) == 64


def test_profile_dataset_uses_catalog_provenance(tmp_path):
    raw_dir = tmp_path / "raw"
    data_dir = raw_dir / "creditcard"
    data_dir.mkdir(parents=True)
    fields = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "Class"]
    pd.DataFrame([{field: 0 for field in fields}]).to_csv(data_dir / "creditcard.csv", index=False)

    profile_dir = tmp_path / "profiles"
    result = profile_dataset("ds1_creditcard", raw_dir, profile_dir)

    assert result["dataset_id"] == "ds1_creditcard"
    assert result["provenance_type"] == "anonymized real transactions"
    assert result["valid"] is False
    saved = json.loads((profile_dir / "ds1_creditcard.json").read_text())
    assert saved["files"][0]["meets_minimum_rows"] is False
