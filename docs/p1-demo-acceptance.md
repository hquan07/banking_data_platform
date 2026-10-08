# Data source status

Runtime-generated transactions, alerts, transfer scenarios, synthetic training
rows and canned API responses have been removed. The dashboard now shows empty
states when no events or records exist. The API returns a service error when a
required datastore is unavailable instead of substituting sample values.

The public benchmark adapter is available as an explicit, source-scoped replay
workflow. DS1, DS3 and DS4 have validated local profiles; DS3 has a reconciled
1,000-row canary plus a controlled 10,000-row increment, while the 1,000-row
DS4 canary has passed. Benchmark replay is opt-in and is not presented as a
live banking feed.

DS1 and DS4 model artifacts are audited offline candidates only. DS4 uses all
30 source features with months 0–5 for training, month 6 for threshold
selection and month 7 for the final holdout. Neither candidate is loaded by
the streaming evaluator or presented as production-ready.

Live payment and transfer sources are still unconfigured. Their Kafka
consumers, contracts, fraud rules, alert workflow and graph processing remain
available for authorized external events. `APP_MODE` accepts `integration` and
`production`; there is no runtime demo mode or `ENABLE_MOCK_DATA` switch.

Static analytics panels that had no data-backed API have been removed. The
Architecture Map remains and distinguishes the dataset replay path from the
unconfigured live payment/transfer path. Replayed records carry dataset and run
provenance; ground-truth labels are stored separately and never passed into the
rule evaluation input.

The original mock-data cleanup was followed by an explicit purge of this
project's Kafka and datastore volumes. The current persisted benchmark records
come only from the documented DS3 and DS4 runs.
