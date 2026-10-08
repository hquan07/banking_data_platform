"""Train an offline DS4 account-fraud candidate with month-based holdouts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from datasets.schema_mapping import DS4_FEATURES


CATEGORICAL_FEATURES = (
    "payment_type",
    "employment_status",
    "housing_status",
    "source",
    "device_os",
)
REQUIRED = ("fraud_bool", "month", *DS4_FEATURES)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_ds4(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, list[str]]]:
    """Validate DS4 and split months 0-5 / 6 / 7 for train/validation/holdout."""
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing DS4 columns: {missing}")

    data = frame.loc[:, list(REQUIRED)].copy()
    numeric_features = [name for name in DS4_FEATURES if name not in CATEGORICAL_FEATURES]
    for column in ("fraud_bool", "month", *numeric_features):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if data[["fraud_bool", "month", *numeric_features]].isna().any().any():
        raise ValueError("DS4 numeric data contains missing values")
    if not data["fraud_bool"].isin([0, 1]).all():
        raise ValueError("fraud_bool must contain only 0 or 1")
    if not data["month"].isin(range(8)).all():
        raise ValueError("month must contain benchmark indices 0 through 7")
    if len(data) < 800:
        raise ValueError("At least 800 DS4 rows are required")

    train_mask = data["month"] <= 5
    validation_mask = data["month"] == 6
    holdout_mask = data["month"] == 7
    train = data.loc[train_mask].copy()
    validation = data.loc[validation_mask].copy()
    holdout = data.loc[holdout_mask].copy()
    for name, split in (("train", train), ("validation", validation), ("holdout", holdout)):
        if split.empty or split["fraud_bool"].nunique() != 2:
            raise ValueError(f"DS4 {name} split must contain positive and negative labels")

    categories: dict[str, list[str]] = {}
    for column in CATEGORICAL_FEATURES:
        if data[column].isna().any():
            raise ValueError(f"DS4 categorical feature {column} contains missing values")
        levels = sorted(train[column].astype(str).unique().tolist())
        if not levels or len(levels) > 255:
            raise ValueError(f"DS4 categorical feature {column} has invalid cardinality")
        categories[column] = levels
        for split in (train, validation, holdout):
            split[column] = pd.Categorical(
                split[column].astype(str), categories=levels,
            )
            if split[column].isna().any():
                raise ValueError(f"DS4 {column} contains a category unseen during training")
    return train, validation, holdout, categories


def _best_f1_threshold(truth: pd.Series, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(truth, scores)
    if not len(thresholds):
        raise ValueError("Unable to derive a DS4 decision threshold")
    denominator = precision[:-1] + recall[:-1]
    f1_values = np.divide(
        2 * precision[:-1] * recall[:-1],
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )
    return float(thresholds[int(np.argmax(f1_values))])


def train_ds4_candidate(
    input_path: Path,
    output_dir: Path,
    version: str,
    max_iter: int = 100,
) -> dict:
    if not version or "/" in version or ".." in version:
        raise ValueError("A safe, nonempty model version is required")
    if not 10 <= max_iter <= 500:
        raise ValueError("max_iter must be between 10 and 500")

    dataset_hash = _sha256_file(input_path)
    frame = pd.read_csv(input_path)
    train, validation, holdout, categories = prepare_ds4(frame)
    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=max_iter,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        categorical_features=list(CATEGORICAL_FEATURES),
        class_weight="balanced",
        early_stopping=False,
        random_state=42,
    )
    model.fit(train[list(DS4_FEATURES)], train["fraud_bool"])

    validation_scores = model.predict_proba(validation[list(DS4_FEATURES)])[:, 1]
    threshold = _best_f1_threshold(validation["fraud_bool"], validation_scores)
    holdout_scores = model.predict_proba(holdout[list(DS4_FEATURES)])[:, 1]
    predicted = holdout_scores >= threshold
    truth = holdout["fraud_bool"].astype(bool)
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[False, True]).ravel()

    metadata = {
        "version": version,
        "dataset_id": "ds4_baf",
        "dataset_sha256": dataset_hash,
        "algorithm": "HistGradientBoostingClassifier",
        "feature_schema": list(DS4_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "categorical_levels": categories,
        "train_months": [0, 1, 2, 3, 4, 5],
        "validation_month": 6,
        "holdout_month": 7,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "holdout_rows": len(holdout),
        "decision_threshold": threshold,
        "metrics": {
            "precision": precision_score(truth, predicted, zero_division=0),
            "recall": recall_score(truth, predicted, zero_division=0),
            "f1": f1_score(truth, predicted, zero_division=0),
            "pr_auc": average_precision_score(truth, holdout_scores),
            "roc_auc": roc_auc_score(truth, holdout_scores),
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0,
            "true_positive": int(tp),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_negative": int(tn),
        },
        "baseline": {
            "train_fraud_rate": float(train["fraud_bool"].mean()),
            "validation_fraud_rate": float(validation["fraud_bool"].mean()),
            "holdout_fraud_rate": float(holdout["fraud_bool"].mean()),
        },
        "status": "CANDIDATE_NOT_DEPLOYED",
        "evaluation_scope": "ds4_month_0_5_train_6_validation_7_holdout",
        "production_eligible": False,
        "explanation_status": (
            "No SHAP or causal explanations are emitted by this candidate pipeline"
        ),
    }

    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=False)
    model_path = version_dir / "model.joblib"
    joblib.dump({
        "model": model,
        "decision_threshold": threshold,
        "feature_schema": list(DS4_FEATURES),
        "categorical_levels": categories,
    }, model_path)
    metadata["model_sha256"] = _sha256_file(model_path)
    (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--max-iter", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(train_ds4_candidate(
        args.csv, args.output_dir, args.version, args.max_iter,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
