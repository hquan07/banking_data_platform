"""Train an offline DS1 Isolation Forest candidate with a relative-time holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
)


FEATURES = tuple(f"V{i}" for i in range(1, 29))
REQUIRED = ("Time", "Amount", "Class", *FEATURES)


def prepare_ds1(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing DS1 columns: {missing}")
    data = frame.loc[:, list(REQUIRED)].copy()
    for column in REQUIRED:
        data[column] = pd.to_numeric(data[column], errors="raise")
    if data.isna().any().any():
        raise ValueError("DS1 data contains missing values")
    if not data["Class"].isin([0, 1]).all():
        raise ValueError("Class must contain only 0 or 1")
    if (data["Time"] < 0).any() or (data["Amount"] < 0).any():
        raise ValueError("Time and Amount must be non-negative")
    if len(data) < 200:
        raise ValueError("At least 200 DS1 rows are required")

    data = data.sort_values("Time", kind="stable").reset_index(drop=True)
    cutoff_position = int(len(data) * 0.8)
    cutoff_time = data.iloc[cutoff_position]["Time"]
    train = data[data["Time"] < cutoff_time]
    holdout = data[data["Time"] >= cutoff_time]
    if train.empty or holdout.empty or len(holdout) < len(data) * 0.1:
        raise ValueError("DS1 relative-time split is too small or degenerate")
    if train["Time"].max() >= holdout["Time"].min():
        raise ValueError("DS1 training and holdout relative times overlap")
    if holdout["Class"].nunique() != 2:
        raise ValueError("DS1 holdout must contain positive and negative labels")
    return train, holdout


def train_ds1_candidate(
    input_path: Path,
    output_dir: Path,
    version: str,
    contamination: float = 0.002,
) -> dict:
    if not version or "/" in version or ".." in version:
        raise ValueError("A safe, nonempty model version is required")
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5")

    dataset_bytes = input_path.read_bytes()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
    frame = pd.read_csv(input_path)
    train, holdout = prepare_ds1(frame)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[list(FEATURES)])
    train_scores = -model.decision_function(train[list(FEATURES)])
    score_threshold = float(pd.Series(train_scores).quantile(1 - contamination))
    holdout_scores = -model.decision_function(holdout[list(FEATURES)])
    predicted = holdout_scores >= score_threshold
    truth = holdout["Class"].astype(bool)
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[False, True]).ravel()

    metadata = {
        "version": version,
        "dataset_id": "ds1_creditcard",
        "dataset_sha256": dataset_hash,
        "feature_schema": list(FEATURES),
        "relative_time_field": "Time",
        "train_time_max": float(train["Time"].max()),
        "holdout_time_min": float(holdout["Time"].min()),
        "holdout_time_max": float(holdout["Time"].max()),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "contamination": contamination,
        "score_threshold": score_threshold,
        "metrics": {
            "precision": precision_score(truth, predicted, zero_division=0),
            "recall": recall_score(truth, predicted, zero_division=0),
            "pr_auc": average_precision_score(truth, holdout_scores),
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0,
            "true_positive": int(tp),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_negative": int(tn),
        },
        "baseline": {
            "feature_mean": {name: float(train[name].mean()) for name in FEATURES},
            "feature_std": {name: float(train[name].std(ddof=0)) for name in FEATURES},
            "ground_truth_positive_rate": float(train["Class"].mean()),
        },
        "status": "CANDIDATE_NOT_DEPLOYED",
        "evaluation_scope": "ds1_relative_time_holdout",
        "production_eligible": False,
        "explanation_status": "No per-feature SHAP values are emitted by this Isolation Forest pipeline",
    }

    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=False)
    model_path = version_dir / "model.joblib"
    joblib.dump({"model": model, "score_threshold": score_threshold}, model_path)
    metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--contamination", type=float, default=0.002)
    args = parser.parse_args()
    print(json.dumps(train_ds1_candidate(
        args.csv, args.output_dir, args.version, args.contamination,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
