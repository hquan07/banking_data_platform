# Kafka storage and topic policy (single-node development stack)

Kafka's KRaft log and metadata live in the `kafka_data` Docker volume. Keep
this volume when restarting or recreating containers. The broker is a single
node, so every topic has replication factor 1; this is durable across container
recreation but **not** highly available.

`kafka_topics_init` creates or verifies four three-partition topics and applies
their retention policy on every Compose startup:

| Topic | Retention | Key |
| --- | --- | --- |
| `payment-events` | 7 days | `payment_id` |
| `payment-events-dlq` | 30 days | none (source partition/offset in payload) |
| `fraud-events` | 30 days | payment or account ID (rule-dependent) |
| `aml-events` | 30 days | account ID |

The initializer refuses an existing topic with a different partition count or
replication factor. Increasing partitions for a keyed topic can change key
ordering, so it needs an explicit migration plan. Invalid payment records go
to the DLQ; failed Spark microbatches retry from their checkpoints. A separate
retry topic and delayed replay worker are not enabled yet.

Both Spark consumers cap each Kafka microbatch at 1,000 offsets by default via
`SPARK_MAX_OFFSETS_PER_TRIGGER`. Tune this against throughput and checkpoint lag;
the cap is per streaming query, not a total across the two applications.

When upgrading an existing installation that had no Kafka volume, stop Kafka
and all producers/consumers first, copy `/bitnami/kafka/data` from the stopped
`banking_kafka` container to a safe backup, then copy that directory into the
new `kafka_data` volume **before** recreating the Kafka container. Compare
topic IDs and end offsets before/after startup; retain the backup until those
checks and a payment E2E test pass. Do not run `docker compose down -v`.
