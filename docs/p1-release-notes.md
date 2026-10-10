# P1 release notes (excluding CI/CD)

## Changes

- Alert cases have versioned transitions, assignee/evidence audit history,
  server-side filtering, and trace IDs. Case and WebSocket authorization use
  current database roles; WebSocket clients send subprotocols `bearer,<JWT>`.
- Customer Silver DQ checks read parquet, quarantine invalid rows, and persist
  run-scoped evidence. Payment and transfer events have explicit v1 contracts
  and DLQs. Approved payment retries use `payment-events-retry`.
- Graph transfer processing is idempotent and detects account cycles. The
  benchmark replay path now handles public datasets; upstream live
  payment/transfer sources remain unconfigured.
- Runtime mock generators, canned API responses, synthetic training/demo
  registry utilities, and static sample dashboard charts have been removed.
  APIs report unavailable dependencies and dashboards show empty states until
  real or intentionally supplied dataset records are available.
- Prometheus/Grafana collect case, Spark batch, DQ, WebSocket and API metrics.
  The dashboard loads tabs on demand and validates incoming stream messages.
- Superset connector installation uses a pinned image and persistent metadata
  volume. Frontend uses `npm ci`; direct Spark and backend Python dependencies
  are pinned. Stateful Compose services use pinned image versions.
- The Architecture Map retains the Banking Data Platform diagram and shows the
  opt-in benchmark replay separately from unconfigured live sources.
- The bounded PaySim benchmark sustained 50 events/second for five minutes.
  Kafka processor/graph peak lag remained at 53/6, both groups drained to zero,
  the DLQ did not grow, and all measured API responses stayed below two seconds.
- The live Compose integration suite passed all eight payment, retry/DLQ,
  alert lifecycle, RBAC, Redis, Neo4j and MinIO end-to-end paths.
- The PostgreSQL backup command now validates a custom archive by restoring it
  into an isolated temporary database and reconciling every application table.

See `docs/p1-demo-acceptance.md` for the current data-source status and the
database-volume cleanup boundary. See `docs/p1-e2e-acceptance.md` for the live
integration evidence and `docs/p1-postgres-recovery-rehearsal.md` for the
recovery workflow and evidence.

## Data migration and rollback

Backend startup applies idempotent SQL files `p1_alert_lifecycle.sql`,
`p1_dq_results.sql` and `p1_trace_context.sql`. Take a PostgreSQL backup before
upgrading. Reverting application code does not drop these additive columns or
tables; dropping them requires an explicit, reviewed migration after export of
audit/DQ records. Retain Spark checkpoint and Kafka volumes during rollback.

For existing Superset installations, stop Superset, copy
`/app/superset_home/superset.db` from the stopped container, verify its hash,
restore it into `banking_data_platform_superset_home`, then recreate the
container. Keep the backup until health and saved dashboards are checked.

Do not delete checkpoint, Kafka or database volumes with `docker compose down
-v`. Existing database records and queued events were not purged as part of
removing mock-data generation because their provenance may be mixed.

## Remaining promotion gates

- A permissioned, labeled fraud dataset and a point-in-time feature pipeline
  are required before approving or deploying an ML model.
- Connect authorized live payment/transfer sources before interpreting the
  platform as a live banking system. Benchmark results remain source-scoped.
- The scoped local benchmark and PostgreSQL recovery rehearsal are complete.
  Longer soak testing, recovery coverage for the other stateful services and a
  security review are still needed before claiming production readiness.
  CI/CD remains out of scope.
