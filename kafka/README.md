# Kafka storage and topic policy (single-node development stack)

Kafka's KRaft log and metadata live in the `kafka_data` Docker volume. Keep
this volume when restarting or recreating containers. The broker is a single
node, so every topic has replication factor 1; this is durable across container
recreation but **not** highly available.

`kafka_topics_init` creates or verifies nine three-partition topics and applies
their retention policy on every Compose startup:

| Topic | Retention | Key |
| --- | --- | --- |
| `payment-events` | 7 days | `payment_id` |
| `payment-events-dlq` | 30 days | none (source partition/offset in payload) |
| `payment-events-retry` | 7 days | `payment_id` |
| `fraud-events` | 30 days | payment or account ID (rule-dependent) |
| `aml-events` | 30 days | account ID |
| `transfer-events` | 7 days | source account ID |
| `transfer-events-dlq` | 30 days | none (source partition/offset in payload) |
| `benchmark-events` | 7 days | stable dataset event ID |
| `benchmark-events-dlq` | 30 days | stable dataset source row ID |

The initializer refuses an existing topic with a different partition count or
replication factor. Increasing partitions for a keyed topic can change key
ordering, so it needs an explicit migration plan. Invalid payment records go
to the DLQ; failed Spark microbatches retry from their checkpoints. An operator
may repair an event and submit it with `python kafka/retry/submit_payment_retry.py
--event-json corrected.json --reason 'approved correction' --approve`. The
retry worker validates it, sends it to `payment-events`, and commits the
retry offset only after the broker acknowledges the write. Invalid retry
envelopes return to DLQ. This is an explicitly approved replay path, **not**
automatic replay of malformed data. A second delivery after a commit failure
is safe because the payment sinks use stable event IDs and idempotent writes.

Both Spark consumers cap each Kafka microbatch at 1,000 offsets by default via
`SPARK_MAX_OFFSETS_PER_TRIGGER`. Tune this against throughput and checkpoint lag;
the cap is per streaming query, not a total across the two applications.
Compose caps each Spark driver container at 2 GiB and the worker at 3 GiB;
adjust these together with Spark executor settings after measuring workload.

Public datasets are replayed only through the opt-in `dataset-replay` Compose
profile. The replay publishes canonical `benchmark-events` and never generates
extra rows. For example, after downloading and profiling DS3:

```bash
DATASET_ID=ds3_paysim DATASET_MAX_EVENTS=1000 \
  docker compose --profile dataset-replay run --rm dataset_replay
```

`DATASET_REPLAY_RATE=0` disables pacing; the default is 50 events per second.
`DATASET_START_ROW` resumes from a deterministic source row. Stable event IDs
and downstream unique constraints provide replay deduplication, but operators must still avoid comparing
metrics from overlapping replay runs unless the run boundary is recorded.
The producer keeps at most `DATASET_MAX_IN_FLIGHT` unacknowledged sends
(default 500), then waits for the oldest Kafka acknowledgement. This preserves
`acks=all` delivery checks without serializing every event behind one ACK.

The Redis velocity counter uses each event's UTC timestamp in a five-minute
sliding sorted set. Retries of an event ID are ignored for seven days; an event
older than the current account window is ignored as late. The Redis window is
diagnostic; the Spark watermark-based velocity rule publishes fraud alerts.
The payment processor quarantines events older than seven days or more than
five minutes in the future as `event_too_late` / `event_in_future`; these are
not silently included in transaction stores. Fraud stateful rules use a
10-minute event-time watermark (one hour for shared-device correlation), so
late records can be stored as payments yet excluded from those aggregations.

When upgrading an existing installation that had no Kafka volume, stop Kafka
and all producers/consumers first, copy `/bitnami/kafka/data` from the stopped
`banking_kafka` container to a safe backup, then copy that directory into the
new `kafka_data` volume **before** recreating the Kafka container. Compare
topic IDs and end offsets before/after startup; retain the backup until those
checks and a payment E2E test pass. Do not run `docker compose down -v`.
