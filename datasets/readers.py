"""Chunked readers for local source files; no rows are generated or sampled."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from datasets.schema_mapping import map_ds1, map_ds2, map_ds3, map_ds4


DEFAULT_CHUNK_SIZE = 5_000


def _records(path: Path, chunk_size: int) -> Iterator[tuple[int, dict[str, Any]]]:
    row_number = 0
    for chunk in pd.read_csv(path, chunksize=chunk_size, low_memory=False):
        for record in chunk.to_dict(orient="records"):
            yield row_number, record
            row_number += 1


def iter_source_rows(
    dataset_id: str,
    raw_dir: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[tuple[int, dict[str, Any], dict[str, Any] | None]]:
    """Yield stable row number, primary row and optional joined identity row."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if dataset_id == "ds1_creditcard":
        path = raw_dir / "creditcard/creditcard.csv"
        for row_number, row in _records(path, chunk_size):
            yield row_number, row, None
        return
    if dataset_id == "ds2_ieee_cis":
        transaction_path = raw_dir / "ieee-cis/train_transaction.csv"
        identity_path = raw_dir / "ieee-cis/train_identity.csv"
        identity_frame = pd.read_csv(identity_path, low_memory=False).set_index("TransactionID", drop=False)
        for row_number, row in _records(transaction_path, chunk_size):
            transaction_id = row.get("TransactionID")
            identity = None
            if transaction_id in identity_frame.index:
                match = identity_frame.loc[transaction_id]
                if isinstance(match, pd.DataFrame):
                    raise ValueError(f"duplicate_identity_TransactionID:{transaction_id}")
                identity = match.to_dict()
            yield row_number, row, identity
        return
    if dataset_id == "ds3_paysim":
        path = raw_dir / "paysim/PS_20174392719_1491204439457_log.csv"
        for row_number, row in _records(path, chunk_size):
            yield row_number, row, None
        return
    if dataset_id == "ds4_baf":
        path = raw_dir / "bank-account-fraud/Base.csv"
        for row_number, row in _records(path, chunk_size):
            yield row_number, row, None
        return
    raise ValueError(f"unknown_dataset_id:{dataset_id}")


def map_source_row(
    dataset_id: str,
    row_number: int,
    row: dict[str, Any],
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if dataset_id == "ds1_creditcard":
        return map_ds1(row, row_number)
    if dataset_id == "ds2_ieee_cis":
        return map_ds2(row, identity)
    if dataset_id == "ds3_paysim":
        return map_ds3(row, row_number)
    if dataset_id == "ds4_baf":
        return map_ds4(row, row_number)
    raise ValueError(f"unknown_dataset_id:{dataset_id}")
