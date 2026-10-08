"""Offline drift and delayed-label checks for synthetic demo candidates only."""

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, precision_score, recall_score

from fraud.scoring.demo_registry import read_registry, verify_candidate
from fraud.scoring.train_model import FEATURES


def monitor_demo(root: Path, input_path: Path) -> dict:
    if os.environ.get("APP_MODE", "integration").lower() == "production":
        raise ValueError("synthetic demo monitoring is forbidden in APP_MODE=production")
    registry = read_registry(root)
    active = registry.get("active")
    if registry.get("scope") != "synthetic_demo_only" or not active:
        raise ValueError("no selected synthetic demo candidate")
    version = active["version"]
    metadata = verify_candidate(root, version)
    if active["model_sha256"] != metadata["model_sha256"]:
        raise ValueError("selected model hash no longer matches candidate")
    frame = pd.read_csv(input_path)
    if "event_time" not in frame:
        raise ValueError("monitoring requires event_time")
    event_times = pd.to_datetime(frame["event_time"], utc=True, errors="raise")
    if not metadata.get("holdout_end_utc") or event_times.min() <= pd.Timestamp(metadata["holdout_end_utc"]):
        raise ValueError("monitoring period must start after the candidate holdout")
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f"missing monitored features: {sorted(missing)}")
    if len(frame) < 20 or "data_origin" not in frame or not frame["data_origin"].eq("synthetic_demo").all():
        raise ValueError("monitoring requires at least 20 synthetic_demo records")
    features = frame[list(FEATURES)].apply(pd.to_numeric, errors="raise")
    if features.isna().any().any():
        raise ValueError("monitored features contain missing values")
    baseline = metadata.get("baseline")
    if not baseline:
        raise ValueError("candidate has no training baseline")
    drift = {
        name: abs(float(features[name].mean()) - baseline["feature_mean"][name])
        / max(baseline["feature_std"][name], 1e-6)
        for name in FEATURES
    }
    result = {
        "scope": "synthetic_demo_only", "version": version,
        "interpretation": "Synthetic drift and performance do not predict real banking performance",
        "threshold": active["threshold"], "rows": len(frame),
        "mean_shift_in_train_std": drift,
        "drift_flags": [name for name, shift in drift.items() if shift >= 1.0],
        "performance": None,
    }
    if "is_fraud" in frame and frame["is_fraud"].notna().all():
        truth = pd.to_numeric(frame["is_fraud"], errors="raise")
        if not truth.isin([0, 1]).all() or truth.nunique() != 2:
            raise ValueError("delayed labels must contain both 0 and 1")
        model = joblib.load(root / version / "model.joblib")
        probability = model.predict_proba(features)[:, 1]
        predicted = probability >= active["threshold"]
        tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
        result["performance"] = {
            "precision": precision_score(truth, predicted, zero_division=0),
            "recall": recall_score(truth, predicted, zero_division=0),
            "pr_auc": average_precision_score(truth, probability),
            "false_positive_rate": fp / (fp + tn),
            "brier_score": brier_score_loss(truth, probability),
            "positive_rate": float(truth.mean()),
            "true_positive": int(tp), "false_positive": int(fp),
            "false_negative": int(fn), "true_negative": int(tn),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--labeled-csv", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(monitor_demo(args.candidates, args.labeled_csv), indent=2))


if __name__ == "__main__":
    main()
