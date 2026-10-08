# Offline fraud model candidates

The repository does not generate training rows. Supply a labeled dataset from
an approved source with the columns `event_time`, `is_fraud`, and the five
features defined in `train_model.py`. `data_origin`, when present, must have a
single value across the file and is copied into candidate metadata.

```bash
python -m fraud.scoring.train_model \
  --labeled-csv /path/to/approved-labeled-data.csv \
  --output-dir /path/to/candidates \
  --version benchmark-v1
```

Training sorts by UTC event time and uses the final 20% as a temporal holdout.
It writes the dataset and model SHA-256 hashes, feature schema, temporal split,
metrics and baseline statistics. The output remains an offline candidate and
is not loaded by the live Spark fraud engine.

The current trainer's five-feature schema is a legacy baseline. Public
datasets with different features must use dataset-specific adapters and
training schemas; do not synthesize missing account, device, location or
velocity fields to make them fit this model. Keep ground-truth labels outside
the streaming inference payload.
