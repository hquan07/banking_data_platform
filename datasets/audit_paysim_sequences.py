#!/usr/bin/env python3
"""Audit PaySim TRANSFER/CASH_OUT assumptions without loading the full CSV in memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["step", "type", "amount", "nameOrig", "nameDest", "isFraud"]


def audit_paysim_sequences(path: Path, chunk_size: int = 250_000) -> dict:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    fraud_parts = []
    row_offset = 0
    for chunk in pd.read_csv(path, usecols=REQUIRED_COLUMNS, chunksize=chunk_size):
        chunk["source_row_number"] = range(row_offset, row_offset + len(chunk))
        row_offset += len(chunk)
        fraud_parts.append(chunk[chunk["isFraud"].eq(1)])

    fraud = pd.concat(fraud_parts, ignore_index=True) if fraud_parts else pd.DataFrame()
    if fraud.empty:
        return {
            "total_rows": row_offset,
            "fraud_rows": 0,
            "fraud_types": {},
            "ordered_same_step_amount_pairs": 0,
            "adjacent_source_row_pairs": 0,
            "linked_participant_pairs": 0,
        }

    next_type = fraud["type"].shift(-1)
    next_step = fraud["step"].shift(-1)
    next_amount = fraud["amount"].shift(-1)
    sequence_mask = (
        fraud["type"].eq("TRANSFER")
        & next_type.eq("CASH_OUT")
        & fraud["step"].eq(next_step)
        & fraud["amount"].eq(next_amount)
    )
    adjacent_mask = sequence_mask & fraud["source_row_number"].add(1).eq(
        fraud["source_row_number"].shift(-1)
    )

    transfers = fraud[fraud["type"].eq("TRANSFER")]
    cashouts = fraud[fraud["type"].eq("CASH_OUT")]
    linked = transfers.merge(
        cashouts,
        left_on="nameDest",
        right_on="nameOrig",
        suffixes=("_transfer", "_cashout"),
    )
    linked = linked[
        linked["step_cashout"].between(linked["step_transfer"], linked["step_transfer"] + 24)
        & linked["amount_transfer"].between(
            linked["amount_cashout"] * 0.80,
            linked["amount_cashout"] * 1.20,
        )
    ]

    return {
        "total_rows": row_offset,
        "fraud_rows": len(fraud),
        "fraud_types": {key: int(value) for key, value in fraud["type"].value_counts().items()},
        "ordered_same_step_amount_pairs": int(sequence_mask.sum()),
        "adjacent_source_row_pairs": int(adjacent_mask.sum()),
        "linked_participant_pairs": len(linked),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("datasets/raw/paysim/PS_20174392719_1491204439457_log.csv"),
    )
    parser.add_argument("--chunk-size", type=int, default=250_000)
    args = parser.parse_args()
    print(json.dumps(audit_paysim_sequences(args.path, args.chunk_size), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
