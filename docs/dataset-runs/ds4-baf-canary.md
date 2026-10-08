# DS4 BAF canary — 2026-10-08

## Source verification

- Kaggle source: `sgpjesus/bank-account-fraud-dataset-neurips-2022`
- License reported by Kaggle CLI: `CC-BY-NC-SA-4.0`
- Provenance: privacy-preserving synthetic benchmark derived from anonymized
  account-opening data
- Local file: `datasets/raw/bank-account-fraud/Base.csv` (excluded from Git)
- SHA-256: `7bf10a37ce07e72e14c1b09e5efee3d27261baff4facc7da767b0474dcf9b809`
- Rows: 1,000,000
- Columns: 32
- Missing required columns: none
- Observed fraud prevalence: 1.1029%
- `device_fraud_count` range: 0 to 0 (constant, not a usable risk signal)

## Kafka canary

- start row: 0
- maximum events: 1,000
- published: 1,000
- rejected to DLQ: 0
- PostgreSQL events: 1,000
- Ground-truth fraud rows in canary: 8
- Neo4j relationships added: 0 (account applications are not transactions)
- `benchmark-processor-v2` lag after reconciliation: 0

## Calibration finding and cleanup

The proposed `date_of_birth_distinct_emails_4w > 3` rule fired on 916 of the
first 1,000 rows. Together with a short-session rule it created 937 alerts,
which demonstrated that the plan's fixed thresholds were not calibrated to
this benchmark.

The evaluator was changed to fail closed for BAF. Exactly 937 DS4 alerts and
1,000 v1 evaluation rows from that rejected rule set were removed. Evaluator
v2 then reprocessed all 1,000 events and produced 1,000 persisted evaluations
with zero predicted fraud. Source rows, full feature payloads and ground truth
were retained for later source-specific model calibration.

## Decision

Ingestion and analytics are accepted; rule-based alerting is not. DS4 remains
an offline account-application benchmark until a temporally split, calibrated
candidate is reviewed. It must not be represented as payment behavior.
