# Retention policy and cleanup controls

This policy applies to the demo platform. It is not a statutory banking-record
schedule. A production deployment must replace these periods with approved
legal, privacy and records-management requirements.

## Safety invariants

- Cleanup is always scoped by one explicit `source` and one timezone-aware
  cutoff. The cutoff comparison is strict: records exactly at the cutoff are
  retained.
- The command is a dry-run unless `--apply-dry-run <execution-id>` is supplied.
  Apply is rejected if the current candidate fingerprint differs from that
  completed dry-run.
- `CREATED`, `RUNNING`, `PAUSING`, `PAUSED` and `CANCELLING` runs are protected.
  Terminal runs on legal hold or linked to an open case are also protected.
- Referenced MinIO evidence is never deleted by automated retention. Every
  object for a pending or investigating case is protected, referenced or not.
- Pipeline-run records, run events, reconciliation records, alert audit and
  retention execution audit remain in the control plane when materialized data
  is purged. Cleanup is retry-safe; a successful run is marked once and is not
  selected again.
- A partial failure is recorded as `FAILED`, including per-store deleted
  counts. Run a new dry-run before retrying; never manually edit the audit row.

## Default schedule

| Store / data | Demo retention | Enforcement and protection |
| --- | ---: | --- |
| Kafka payment, transfer, retry and benchmark topics | 7 days | `kafka/init-topics.sh` reapplies `retention.ms`; no source-selective record deletion. |
| Kafka DLQ, fraud and AML topics | 30 days | Topic retention; longer than normal topics for investigation and replay. |
| PostgreSQL benchmark events/evaluations | 30 days after terminal run | Source-scoped cleanup; active/paused, legal-hold and open-case runs excluded. |
| PostgreSQL canonical live payments | 90 days | `live_payment` cleanup by event timestamp; events linked to open cases excluded. |
| PostgreSQL cases, comments, evidence metadata and audit | 365 days after case closure | Not automatically deleted in P2-0601; referenced evidence metadata remains authoritative. |
| PostgreSQL run/reconciliation/retention control records | 365 days minimum | Metadata is retained when materialized data is purged. |
| ClickHouse `payment_events` | 90 days | `live_payment` cleanup mirrors the same cutoff/open-case event exclusions. |
| Neo4j DS3 relationships and run-isolated nodes | 30 days after terminal run | Deleted only for the exact candidate run IDs approved by dry-run. |
| MinIO referenced case evidence | 365 days after closure, then policy review | Automated cleanup never deletes a referenced object. |
| MinIO unreferenced uploads | 7 days | Eligible only under a known source/closed case prefix and explicit cutoff. |
| MinIO Silver data | 30 days where partitioned | Current customer Silver path is overwrite-based; no blind recursive deletion. |
| Spark checkpoints | Life of the streaming query plus one recovery cycle | Automatic cleanup is disabled. Remove only after the application is stopped, Kafka offsets are recorded and recovery evidence is captured. |

Kafka retention must exceed the maximum expected processor outage. Changing a
topic period requires updating `kafka/init-topics.sh`, restarting
`kafka_topics_init`, and recording the topic description. Spark checkpoints and
Kafka offsets form one recovery boundary and must never be cleaned separately.

## Legal hold

Administrators can set or release a hold through:

```text
POST /api/runs/{run_id}/legal-hold
{"enabled": true, "version": 3, "reason": "Open compliance review"}
```

The operation uses optimistic locking, increments the run version and appends a
`LEGAL_HOLD` run event. Enabling a hold requires a reason. Releasing a hold does
not make a run immediately eligible: terminal state, cutoff and open-case rules
still apply.

## Dry-run and apply

Load the project environment, then plan one source. The command writes a
`DRY_RUN` audit row but does not remove data:

```bash
python3 scripts/retention_cleanup.py \
  --source ds3_paysim \
  --cutoff 2026-08-01T00:00:00Z
```

Review `candidate_run_ids`, every store count, protected reasons and the
fingerprint. Apply that exact plan by referencing its execution ID:

```bash
python3 scripts/retention_cleanup.py \
  --source ds3_paysim \
  --cutoff 2026-08-01T00:00:00Z \
  --apply-dry-run 00000000-0000-0000-0000-000000000000
```

Use source `live_payment` for PostgreSQL and ClickHouse live events. Other
benchmark sources use their dataset IDs, such as `ds1_creditcard` or
`ds4_baf`. The command does not delete Kafka records, Silver paths or Spark
checkpoints because those stores cannot currently satisfy the same safe
source/run boundary.

## Audit and verification

Each invocation records one `retention_executions` row and one
`retention_execution_items` row per store. Administrators can inspect them via
`GET /api/retention/executions` and
`GET /api/retention/executions/{execution_id}`.

After apply:

1. Confirm the execution is `COMPLETED` and deleted counts do not exceed the
   approved candidates.
2. Confirm candidate runs retain control metadata and have
   `retention_purged_at` plus a `RETENTION_PURGED` event.
3. Re-run dry-run with the same scope. Successfully purged runs must appear as
   `already_purged` and all corresponding store candidate counts must be zero.
4. Verify open cases and their MinIO evidence still resolve before closing the
   change record.
