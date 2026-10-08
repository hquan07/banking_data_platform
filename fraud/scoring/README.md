# ML candidate policy

Live ML alerts are disabled. The old `fraud_model.pkl` was trained with synthetic
labels and is **not approved for inference**; deterministic rules continue to run.
Do not treat previous `ML_MODEL_FRAUD` cases as validated model findings.

`train_model.py` accepts an explicit, trusted CSV with `event_time`, `is_fraud`
(confirmed 0/1 outcome), and the five feature columns listed in the script. It
rejects missing/invalid data, sorts by UTC event time, keeps the last 20% as a
strict temporal holdout, and writes a candidate model and metadata into a new
version directory. Metadata contains the dataset and artifact SHA-256 hashes,
feature schema, threshold, confusion counts, precision, recall, PR-AUC, false
positive rate, and Brier calibration score. It does **not** register or deploy
the candidate.

Before enabling inference, supply permissioned historical labels and implement
the same point-in-time features in serving, including account profile, device,
location, and graph context. Then review holdout performance, approve an
artifact registry and rollback procedure, and monitor drift and delayed-label
performance. No production metric is claimed until those inputs exist.
