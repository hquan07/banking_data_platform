#!/usr/bin/env python3
"""Chunked, provenance-aware profiling for the local benchmark datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DATASETS_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = DATASETS_DIR / "raw"
DEFAULT_PROFILE_DIR = DATASETS_DIR / "profiles"
DISTINCT_CAP = 10_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _new_column_state() -> dict[str, Any]:
    return {
        "missing_count": 0,
        "non_null_count": 0,
        "numeric_count": 0,
        "numeric_sum": 0.0,
        "numeric_min": None,
        "numeric_max": None,
        "distinct_values": set(),
        "distinct_capped": False,
    }


def _update_column(state: dict[str, Any], series: pd.Series) -> None:
    state["missing_count"] += int(series.isna().sum())
    values = series.dropna()
    state["non_null_count"] += len(values)

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    state["numeric_count"] += len(numeric)
    if len(numeric):
        current_min = float(numeric.min())
        current_max = float(numeric.max())
        state["numeric_sum"] += float(numeric.sum())
        state["numeric_min"] = current_min if state["numeric_min"] is None else min(state["numeric_min"], current_min)
        state["numeric_max"] = current_max if state["numeric_max"] is None else max(state["numeric_max"], current_max)

    if not state["distinct_capped"]:
        remaining = DISTINCT_CAP + 1 - len(state["distinct_values"])
        if remaining > 0:
            state["distinct_values"].update(values.astype(str).drop_duplicates().head(remaining))
        if len(state["distinct_values"]) > DISTINCT_CAP:
            state["distinct_capped"] = True
            state["distinct_values"].clear()


def profile_csv(
    path: Path,
    required_columns: list[str] | None = None,
    minimum_rows: int = 1,
    chunk_size: int = 100_000,
) -> dict[str, Any]:
    required = required_columns or []
    states: dict[str, dict[str, Any]] = {}
    row_count = 0

    for chunk in pd.read_csv(path, chunksize=chunk_size, low_memory=False):
        row_count += len(chunk)
        for name in chunk.columns:
            state = states.setdefault(name, _new_column_state())
            _update_column(state, chunk[name])

    columns = []
    for name, state in states.items():
        non_null = state["non_null_count"]
        numeric_count = state["numeric_count"]
        if non_null == 0:
            inferred_kind = "empty"
        elif numeric_count == non_null:
            inferred_kind = "numeric"
        elif numeric_count == 0:
            inferred_kind = "categorical"
        else:
            inferred_kind = "mixed"
        numeric_mean = state["numeric_sum"] / numeric_count if numeric_count else None
        columns.append({
            "name": name,
            "inferred_kind": inferred_kind,
            "missing_count": state["missing_count"],
            "missing_rate": round(state["missing_count"] / row_count, 8) if row_count else None,
            "distinct_count": None if state["distinct_capped"] else len(state["distinct_values"]),
            "distinct_count_capped_at": DISTINCT_CAP if state["distinct_capped"] else None,
            "numeric_min": state["numeric_min"],
            "numeric_max": state["numeric_max"],
            "numeric_mean": numeric_mean,
        })

    observed = set(states)
    missing_columns = sorted(set(required) - observed)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "row_count": row_count,
        "column_count": len(states),
        "required_columns": required,
        "missing_required_columns": missing_columns,
        "unexpected_columns": sorted(observed - set(required)) if required else [],
        "minimum_rows": minimum_rows,
        "meets_minimum_rows": row_count >= minimum_rows,
        "valid": not missing_columns and row_count >= minimum_rows,
        "columns": columns,
    }


def profile_dataset(
    dataset_id: str,
    raw_dir: Path = DEFAULT_RAW_DIR,
    profile_dir: Path = DEFAULT_PROFILE_DIR,
) -> dict[str, Any]:
    catalog = json.loads((DATASETS_DIR / "catalog.json").read_text())
    expectations = json.loads((DATASETS_DIR / "schema_expectations.json").read_text())
    entry = next((item for item in catalog["datasets"] if item["id"] == dataset_id), None)
    if entry is None:
        raise ValueError(f"Unknown dataset ID: {dataset_id}")

    file_profiles = []
    for relative_path, rules in expectations[dataset_id].items():
        path = raw_dir / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Missing dataset file: {path}")
        result = profile_csv(
            path,
            required_columns=rules["required_columns"],
            minimum_rows=rules["minimum_rows"],
        )
        result["path"] = relative_path
        file_profiles.append(result)

    profile = {
        "profile_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset_id,
        "source": entry["source"],
        "provenance_type": entry["provenance_type"],
        "valid": all(item["valid"] for item in file_profiles),
        "files": file_profiles,
    }
    profile_dir.mkdir(parents=True, exist_ok=True)
    output = profile_dir / f"{dataset_id}.json"
    output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n")
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="Dataset ID from catalog.json, or 'all'")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    args = parser.parse_args()

    catalog = json.loads((DATASETS_DIR / "catalog.json").read_text())
    ids = [item["id"] for item in catalog["datasets"]]
    selected = ids if args.dataset == "all" else [args.dataset]
    failed = False
    for dataset_id in selected:
        try:
            profile = profile_dataset(dataset_id, args.raw_dir, args.profile_dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"{dataset_id}: ERROR: {exc}")
            failed = True
            continue
        status = "VALID" if profile["valid"] else "INVALID"
        print(f"{dataset_id}: {status}")
        failed = failed or not profile["valid"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
