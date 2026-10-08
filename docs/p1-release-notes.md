# P1 release notes (excluding CI/CD)

## Changes

- Alert cases now have versioned transitions, assignee/evidence audit history,
  server-side filtering, and trace IDs. Case and WebSocket authorization use
  current database roles; WebSocket clients send subprotocols `bearer,<JWT>`.
- Customer Silver DQ checks read real parquet, quarantine invalid rows, and
  persist run-scoped evidence. Payment and transfer events have explicit v1
  contracts and DLQs. Approved payment retries use `payment-events-retry`.
- Graph transfer processing is idempotent and creates cases for 3–5 account
  cycles. A reproducible synthetic transfer generator exercises that path;
  a real upstream transfer producer is still needed for production.
- Synthetic ML inference is disabled and its tracked model artifact removed.
  Offline training on labeled synthetic data produces a demo-only candidate
  with temporal holdout metrics. A checksum-verified offline demo registry,
  threshold history/rollback, drift and delayed-label monitoring exercise the
  workflow without approving or deploying the model. The fake weekly Airflow
  retraining/deployment DAG was removed.
- Prometheus/Grafana now collect case, Spark batch, DQ, WebSocket and API
  metrics. The dashboard loads tabs on demand, validates incoming stream
  messages, shows loading/error/empty states, and labels illustrative charts.
- Superset connector installation moved into a pinned image, and metadata is
  mounted on a persistent named volume. Frontend uses `npm ci`; direct Spark
  and backend Python dependencies are pinned. Stateful Compose services use
  the exact digests of the images running when this release was verified.
- Dashboard charts explicitly identify simulated values, the Architecture Map
  retains the Banking Data Platform diagram, and frontend lint/dependency
  hygiene is in place. The backend uses patched authentication/form packages.

See `docs/p1-demo-acceptance.md` for the verification snapshot, mock-data
acceptance boundary and the remaining live test login gap.

## Data migration and rollback

Backend startup applies idempotent SQL files `p1_alert_lifecycle.sql`,
`p1_dq_results.sql` and `p1_trace_context.sql`. Take a PostgreSQL backup before
upgrading. Reverting the application code does not drop these additive columns
or tables; dropping them requires an explicit, reviewed migration after export
of audit/DQ records. Retain Spark checkpoint and Kafka volumes during rollback.

For existing Superset installations, stop Superset, copy
`/app/superset_home/superset.db` from the stopped container, verify its hash,
restore it into `banking_data_platform_superset_home`, then recreate the
container. Keep the backup until health and saved dashboards are checked. The
new volume is `banking_data_platform_superset_home`. SQLite metadata
is retained for this development stack; it is not a production HA design.

The retry worker can be stopped independently. Any unconsumed retry records
remain in Kafka for seven days. Do not delete checkpoint, Kafka or database
volumes with `docker compose down -v`.

## Remaining promotion gates

- A permissioned, labeled fraud dataset and a real-time point-in-time feature
  pipeline are required before approving or deploying an ML model. The offline
  synthetic registry/monitor is not a production model-serving system.
  Existing synthetic ML cases require analyst review.
- Integrate a real transfer-event producer; the graph pipeline currently has
  live E2E coverage with test events, not a production source.
- Load testing, backup/restore rehearsal and a security review are still needed
  before claiming production readiness. CI/CD was explicitly out of scope.
