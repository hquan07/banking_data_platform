# P1 demo acceptance (CI/CD excluded)

This project uses synthetic banking events and labels only. P1 here means an
end-to-end **demonstration of the engineering workflow**, not validation of a
fraud model on real customers and not production readiness. Keep
`APP_MODE=integration` for connected-service tests; the input events can still
be synthetic. `APP_MODE=demo` allows explicitly documented fallback responses.
Never ingest real customer data into this stack.

## What can be accepted with mock data

| Area | Demo acceptance evidence | Boundary |
| --- | --- | --- |
| Kafka/Spark reliability | Versioned payment/transfer contracts, DLQ and approved retry, checkpointing, idempotent graph replay, live integration tests | Load, sustained lag and failure-recovery SLOs are not proven by small fixtures. |
| Silver data quality | Parquet-based expectations, quarantine, persisted run evidence and contract tests | Fixture quality is not the quality of a real source feed. |
| Alert/case lifecycle | Versioned state transitions, role checks, audit/evidence history, filters and trace IDs | The alert-lifecycle live E2E still requires a working admin test login on this existing database. |
| Fraud ML governance | Reproducible labeled synthetic CSV, strict temporal holdout, artifact/dataset hashes, offline candidate registry, threshold history/rollback, post-holdout drift and delayed-label metrics | `data_origin=synthetic_demo`, `evaluation_scope=pipeline_test_only`, `production_eligible=false`; no live inference or real-world precision claim. |
| AML graph | Synthetic 3/4/5-account cycles and a negative control sent as transfer-events v1; idempotent processor and case creation | No real upstream transfer system is connected. |
| Observability and UI | Prometheus/Grafana, service readiness, dashboard loading/error states, explicit DEMO DATA and illustrative chart labels, Banking Data Platform architecture diagram | Dashboard visualizations do not establish production throughput or accuracy. |
| Dependency hygiene | Pinned packages, frontend lint/build/test, backend and frontend dependency audits | Root Spark Python/runtime version alignment and remaining root dependency advisories need a separate, tested upgrade. CI/CD was excluded. |

## Reproduce the offline ML demo

Follow `fraud/scoring/README.md` to generate a January training fixture, train a
candidate, select a demo-only threshold, monitor a February labeled fixture,
change threshold and roll back. The monitor rejects a batch overlapping the
training holdout. Registry and monitor refuse `APP_MODE=production`; the live
Spark fraud engine never loads this candidate. Perfect metrics are possible
because the synthetic labels are scripted; report them only as pipeline-test
results.

Follow `aml/graph/README.md` for dry-run transfer scenarios. Publishing to
Kafka requires the explicit `--publish` flag and is disabled in production
mode. The dashboard Architecture Map names this as a synthetic generator and
continues to show the Banking Data Platform topology.

## Verification snapshot (2026-10-08)

- Python unit and data-quality suite: 42 passed, 1 skipped on the host (ML
  dependency absent there); the actual offline ML CLI was exercised in the
  Spark container, which has pandas and scikit-learn.
- Frontend: ESLint, Vite production build and Node test all passed; `npm audit`
  reported zero known vulnerabilities.
- Backend dependency audit reported zero known vulnerabilities; backend
  readiness reported PostgreSQL, Kafka, Redis, Neo4j, ClickHouse and MinIO up.
- After the backend upgrade, 6 live E2E tests passed: payment, AML graph,
  payment DLQ/retry, MinIO and Redis velocity. The alert-lifecycle E2E failed
  at normal login with HTTP 401: the persisted admin account password differs
  from the current `.env` value. Do not bypass authentication or reset the
  existing database just to pass it.

## Remaining acceptance input and production-only work

To close the single alert-lifecycle E2E gap, provide a valid admin test login
for the persisted demo database, or explicitly authorize a controlled test
account/password change after backup. Then rerun that test through normal
login. The state-machine implementation and unit tests are in place, but this
live path is not yet verified on this database.

The root Python dependency audit still reports advisories for PySpark 3.5.0
and transitive fsspec 2024.2.0. The running Spark image uses a different 3.5.x
patch level; changing only the Python package would create an unverified
runtime mismatch. Treat this as a known demo-stack exception until both sides
can be upgraded and tested together.

Real source contracts, permissioned and confirmed labels, point-in-time
features, model approval, security review, backup/restore rehearsal and load
testing remain separate promotion gates. No synthetic candidate is eligible
for real fraud decisions.
