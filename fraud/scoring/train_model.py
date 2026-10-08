"""Train an offline candidate only from trusted, labeled historical payments.

The output is deliberately not activated for live scoring. Promotion requires
review of the holdout metrics and a serving feature pipeline with the same schema.
"""

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
)


FEATURES = (
    "amount", "hour_of_day", "velocity_1h", "diff_from_avg", "is_international"
)
REQUIRED = (*FEATURES, "event_time", "is_fraud")


def prepare_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required labeled-data columns: {sorted(missing)}")
    data = frame.loc[:, list(REQUIRED)].copy()
    data["event_time"] = pd.to_datetime(data["event_time"], utc=True, errors="raise")
    if data.isna().any().any():
        raise ValueError("Labeled data contains missing values")
    if not data["is_fraud"].isin([0, 1]).all():
        raise ValueError("is_fraud must contain only 0 or 1")
    for feature in FEATURES:
        data[feature] = pd.to_numeric(data[feature], errors="raise")
    if (data["amount"] <= 0).any() or (data["velocity_1h"] < 0).any():
        raise ValueError("Invalid amount or velocity")
    if not data["hour_of_day"].between(0, 23).all():
        raise ValueError("hour_of_day must be between 0 and 23")
    if not data["is_international"].isin([0, 1]).all():
        raise ValueError("is_international must contain only 0 or 1")
    data = data.sort_values("event_time", kind="stable").reset_index(drop=True)
    if len(data) < 200:
        raise ValueError("At least 200 labeled records are required")
    split = int(len(data) * 0.8)
    train, holdout = data.iloc[:split], data.iloc[split:]
    if train["event_time"].max() >= holdout["event_time"].min():
        raise ValueError("Training and holdout timestamps overlap")
    if train["is_fraud"].nunique() != 2 or holdout["is_fraud"].nunique() != 2:
        raise ValueError("Both periods must contain positive and negative labels")
    return train, holdout


def train_candidate(input_path: Path, output_dir: Path, version: str, threshold: float) -> dict:
    if not version or "/" in version or ".." in version:
        raise ValueError("A safe, nonempty model version is required")
    if not 0 < threshold < 1:
        raise ValueError("Threshold must be between 0 and 1")
    dataset_bytes = input_path.read_bytes()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
    train, holdout = prepare_data(pd.read_csv(input_path))
    model = RandomForestClassifier(
        n_estimators=100, max_depth=10, class_weight="balanced", random_state=42
    )
    model.fit(train[list(FEATURES)], train["is_fraud"])
    probability = model.predict_proba(holdout[list(FEATURES)])[:, 1]
    predicted = probability >= threshold
    truth = holdout["is_fraud"]
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    metadata = {
        "version": version,
        "dataset_sha256": dataset_hash,
        "feature_schema": list(FEATURES),
        "train_end_utc": train["event_time"].max().isoformat(),
        "holdout_start_utc": holdout["event_time"].min().isoformat(),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "threshold": threshold,
        "metrics": {
            "precision": precision_score(truth, predicted, zero_division=0),
            "recall": recall_score(truth, predicted, zero_division=0),
            "pr_auc": average_precision_score(truth, probability),
            "false_positive_rate": fp / (fp + tn),
            "brier_score": brier_score_loss(truth, probability),
            "true_positive": int(tp), "false_positive": int(fp),
            "false_negative": int(fn), "true_negative": int(tn),
        },
        "status": "CANDIDATE_NOT_DEPLOYED",
    }
    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=False)
    model_path = version_dir / "model.joblib"
    joblib.dump(model, model_path)
    metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labeled-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--threshold", type=float, default=0.7)
    args = parser.parse_args()
    print(json.dumps(train_candidate(args.labeled_csv, args.output_dir, args.version, args.threshold), indent=2))
