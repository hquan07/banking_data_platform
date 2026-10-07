# Payment stream recovery

`payment-events` is validated by the payment processor. Invalid JSON, missing
required fields and unsupported schema versions go to `payment-events-dlq` with
`raw_value`, `validation_error`, source topic, partition and offset. The DLQ
records are never fed automatically back into the input topic.

The payment processor and fraud engine each have their own durable checkpoint
directory on the shared `spark_checkpoints` Docker volume. Keep this volume
when restarting the stack. A failed Spark job restarts with its checkpoint and
retries the unfinished microbatch. Run one instance of each query group; do
not start another instance against the same checkpoint.

To replay corrected DLQ records, extract each `raw_value` into a JSONL file,
fix it to match `shared/payment_contract.md`, and retain its original IDs.
Run `python3 -m scripts.replay_payment_events corrected.jsonl` to validate,
then add `--publish` to send. Check the payment row and alert in the dashboard.
The replay command is safe to repeat after idempotent persistence is enabled.

The processor writes payment rows to PostgreSQL and to ClickHouse
`payment_events`. ClickHouse uses `ReplacingMergeTree`; queries that need a
deduplicated view use `FINAL`. After the stream catches up, run
`python3 -m scripts.reconcile_payment_events` from the host with `.env` filled
in to compare the latest 1,000 events per Kafka partition against both stores.
The command is read-only and exits nonzero when sampled payment IDs are
missing or have different event IDs. Allow for ingestion lag before treating a
newly published payment as a discrepancy.
