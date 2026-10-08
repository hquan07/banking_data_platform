# ML candidate policy

Live ML alerts are disabled. The old `fraud_model.pkl` was trained with synthetic
labels and is **not approved for inference**; deterministic rules continue to run.
The scheduled Airflow DAG that generated random training metrics and claimed
deployment has been removed.
Do not treat previous `ML_MODEL_FRAUD` cases as validated model findings.

For this demo-only project, generate reproducible synthetic labels and run the
offline training workflow:

```bash
python3 -m fraud.scoring.demo_dataset --output /tmp/banking-demo-labeled.csv --seed 42
python3 -m fraud.scoring.train_model --labeled-csv /tmp/banking-demo-labeled.csv \
  --output-dir /tmp/banking-demo-candidates --version demo-v1
python3 -m fraud.scoring.demo_registry --candidates /tmp/banking-demo-candidates \
  select --version demo-v1 --threshold 0.7
python3 -m fraud.scoring.demo_dataset --output /tmp/banking-demo-later.csv \
  --seed 99 --start-time 2026-02-01T00:00:00Z
python3 -m fraud.scoring.demo_monitor --candidates /tmp/banking-demo-candidates \
  --labeled-csv /tmp/banking-demo-later.csv
python3 -m fraud.scoring.demo_registry --candidates /tmp/banking-demo-candidates \
  select --version demo-v1 --threshold 0.8
python3 -m fraud.scoring.demo_registry --candidates /tmp/banking-demo-candidates rollback
```

The fixture carries `data_origin=synthetic_demo`; candidate metadata records
`evaluation_scope=pipeline_test_only` and `production_eligible=false`. Its
precision, recall, PR-AUC and calibration demonstrate the evaluation code, not
real-world fraud-detection performance. Spark does not load the candidate or
create live cases from it.
The demo registry stores a checksum-verified candidate pointer, threshold and
selection history in `demo_registry.json`. Its rollback restores the previous
version/threshold pair. The monitor refuses data overlapping the training
holdout, compares feature means to the training baseline and calculates metrics
only when the later synthetic batch has labels. Neither command runs in
`APP_MODE=production`. Use a persistent, ignored directory rather than `/tmp`
if you want the demo artifacts to survive container recreation.

`train_model.py` accepts an explicit CSV with `event_time`, `is_fraud`
(confirmed 0/1 outcome), and the five feature columns listed in the script. It
rejects missing/invalid data, sorts by UTC event time, keeps the last 20% as a
strict temporal holdout, and writes a candidate model and metadata into a new
version directory. Metadata contains the dataset and artifact SHA-256 hashes,
feature schema, threshold, confusion counts, precision, recall, PR-AUC, false
positive rate, Brier calibration score, and data origin. It does **not** register or deploy
the candidate.

For a reviewed, permissioned dataset and an environment with pandas,
scikit-learn and joblib installed:

```bash
python -m fraud.scoring.train_model --labeled-csv /secure/path/labeled.csv \
  --output-dir /secure/path/candidates --version review-2026-10-08
```

Before enabling inference, supply permissioned historical labels and implement
the same point-in-time features in serving, including account profile, device,
location, and graph context. Then review holdout performance, approve an
artifact registry and rollback procedure, and monitor drift and delayed-label
performance. No production metric is claimed until those inputs exist.
