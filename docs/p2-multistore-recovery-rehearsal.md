# Multi-store recovery rehearsal

## Purpose and safety boundary

The recovery runner verifies that the demo platform can reconstruct every
durable data shape without replacing the live Compose stores. It creates only
temporary databases, topics, consumer groups, buckets, volumes and containers,
then removes them before returning.

Raw PostgreSQL, ClickHouse and Spark backup artifacts exist only in an OS
temporary directory. `.runtime/backups/recovery_<timestamp>/` contains exactly
two durable evidence files:

- `manifest.json`: store inventories, counts and SHA-256 digests;
- `report.json`: ordered stage status, duration and final result.

Neither file contains credentials or event payloads. `.runtime/` remains
git-ignored.

## Restore order

The runner always applies the selected stores in this order:

1. Kafka topic configuration and recoverable consumer offsets;
2. PostgreSQL control plane and operational records;
3. MinIO lake/evidence/checkpoint buckets;
4. ClickHouse analytical projections;
5. Neo4j graph projections;
6. Spark streaming checkpoints;
7. cross-store reconciliation for the newest completed durable run.

Kafka must exist before offsets or checkpoints can be meaningful. PostgreSQL
and object storage are restored before the two derived serving stores. Spark
checkpoints come last so a restarted processor cannot advance from a checkpoint
before its inputs and outputs are present. Reconciliation is the traffic-open
gate.

## Run the ordered rehearsal

Start the Compose stack, load `.env`, and run from the repository root:

```bash
python3 scripts/backup/rehearse_multistore_restore.py
```

Run one or more isolated adapters during diagnosis:

```bash
python3 scripts/backup/rehearse_multistore_restore.py \
  --stores postgresql clickhouse --skip-reconciliation
```

The command exits non-zero and writes a failure report if a restore count,
manifest digest, Kafka offset, checkpoint snapshot or reconciliation result is
not exact. Spark writers must be quiesced and the command retried if checkpoint
files change while their snapshot is created.

To exercise the opt-in integration suite:

```bash
RUN_RECOVERY_E2E=1 python3 -m pytest \
  tests/integration/test_live_multistore_recovery.py -q
```

## What each adapter proves

- PostgreSQL creates a custom-format dump, restores it into a temporary
  database and compares every application table row count.
- Kafka recreates each non-internal topic with its partition, replication and
  critical effective configuration, then restores every durable offset from
  each source consumer group into an isolated temporary group and reads it
  back.
- MinIO recreates the three application buckets and server-side copies every
  object while comparing key, size, ETag, content type and metadata. Empty
  buckets are valid; a temporary canary still exercises object write,
  server-side copy and read-back inside the isolated target bucket.
- ClickHouse exports every table in Native format, applies its DDL to a
  temporary database, imports all rows and compares counts.
- Neo4j exports the complete property graph in bounded pages, replays all nodes
  and relationships into a separate temporary Neo4j instance and compares a
  canonical graph digest. Source labels, relationship types and properties are
  preserved in the portable recovery envelope.
- Spark archives the named checkpoint volume, restores it into a temporary
  volume and compares the SHA-256 manifest of every file.
- Reconciliation invokes the existing reconciliation service for the newest
  completed run with durable Kafka offsets and requires every result to be
  `EXACT`.

## Production boundary

This is recovery evidence for the local demo, not a production backup system.
Kafka message logs are not copied: the runner records and rehearses topic
configuration and consumer offsets against the existing retained logs. Neo4j
uses a portable logical envelope rather than Enterprise online backup. A
production design still needs encrypted, off-host, versioned backups; declared
RPO/RTO; retention locks; scheduled restore drills; and supported native backup
tools for the selected editions.
