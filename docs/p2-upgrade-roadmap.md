# P2 improvement and upgrade roadmap

## Objective

Move the project from a validated local integration platform to a reproducible,
observable and security-reviewed pre-production system. The roadmap preserves
the current source boundaries: DS1, DS3 and DS4 are benchmark datasets; live
payment and transfer data is not considered connected until an authorized
external source is onboarded.

## Verified baseline — 2026-10-10

- All long-running Compose services are up; Spark master and worker are healthy.
- `PaymentStreamingProcessor` and `FraudDetectionEngine` are registered with
  Spark and remain at restart count zero after the full integration run.
- Backend readiness verifies PostgreSQL, Kafka, Redis, Neo4j, ClickHouse,
  MinIO, live ingestion and the required Spark applications.
- Backend unit suite: 62 passed, 3 intentionally skipped.
- Data-quality suite: 7 passed.
- Live integration suite: 11 passed.
- Frontend lint, unit tests and production build pass; Playwright: 2 passed.

This baseline is suitable for continued development and controlled demos. It
is not yet a production-readiness claim.

## Delivery principles

1. Complete and commit one workstream before starting the next.
2. Every runtime dependency must have a real health signal and an alert.
3. Benchmark, replay and live data must remain explicitly source-scoped.
4. No release is promoted unless unit, data-quality, integration and browser
   gates all pass from a clean checkout.
5. Stateful upgrades require a tested backup and rollback path.

## Phase 0 — Stabilization and reproducibility

Target: 2–3 working days.

### P2-001: Close the current working tree

- Review and commit the pending Architecture Map, topology status and E2E
  changes as one coherent feature.
- Ensure `git status` is clean after generated test artifacts are ignored.
- Re-run the complete acceptance matrix from a fresh checkout.

Exit criteria: a clean branch reproduces the current dashboard and all tests
pass without relying on uncommitted files.

### P2-002: Make CI a blocking acceptance gate

- Upgrade GitHub Actions to maintained major versions.
- Replace `npm install` with `npm ci`.
- Run Python unit tests, data-quality tests, frontend lint/unit/build and
  `docker compose config --quiet` on every pull request.
- Add a Compose-backed job for the 11 live integration tests and Playwright.
- Make critical/high dependency findings blocking, with an explicit and
  reviewed exception file instead of `exit-code: 0`.
- Upload Playwright traces, pytest reports and container logs on failure.

Exit criteria: merge is blocked unless every acceptance gate passes.

### P2-003: Complete runtime observability

- Export Spark master, worker and application state to Prometheus.
- Alert on missing workers, missing required applications, restart growth,
  streaming query termination and checkpoint age.
- Add Kafka publish/consume rates, end-to-end event latency and DLQ growth to
  the operations dashboard.
- Show the Spark dependency and its active applications in Platform Health.

Exit criteria: the failure fixed in commit `10fa5332` is visible within one
minute and pages the operator before data freshness is violated.

### P2-004: Run a soak and fault-injection gate

- Run a two-hour soak first, followed by a 24-hour pre-production soak.
- Exercise controlled restarts of Kafka, Spark worker, PostgreSQL and Neo4j.
- Verify no duplicate canonical events, checkpoint corruption or permanent
  consumer lag after recovery.
- Record throughput, p95/p99 latency, memory, CPU, restart count and DLQ growth.

Exit criteria: 24 hours with no unplanned restart, no lost accepted event and
all consumer groups drained after each fault.

## Phase 1 — Data reliability and governance

Target: 1–2 weeks after Phase 0.

### P2-101: Versioned event contracts

- Add machine-readable schemas for payment, transfer, fraud, AML and benchmark
  events.
- Enforce backward-compatible changes in CI.
- Quarantine incompatible messages with reason, source and trace ID.

### P2-102: Reconciliation and freshness controls

- Reconcile Kafka accepted counts against PostgreSQL, ClickHouse, Neo4j and
  generated alerts by run/window.
- Persist freshness, completeness, uniqueness and schema-conformance results.
- Add dashboard indicators for stale or partially reconciled datasets.

### P2-103: Replay lifecycle

- Give every replay a durable run ID, owner, dataset version, evaluator version
  and terminal status.
- Add pause/cancel/resume with idempotent offsets.
- Prevent concurrent replay runs from mixing metrics or graph namespaces.

### P2-104: Retention and disaster recovery

- Define retention policies for Kafka, ClickHouse, Neo4j, MinIO and Spark
  checkpoints.
- Extend the existing PostgreSQL rehearsal to every stateful dependency.
- Encrypt backups and document restore ordering.

Exit criteria: a run-level reconciliation report is complete, and each
stateful service has a verified restore procedure with recorded evidence.

## Phase 2 — Dashboard and operator experience

Target: 1 week after Phase 1 contracts settle.

### P2-201: Capability-driven navigation

- Serve a backend capability manifest describing which datasets support each
  tab and operation.
- Derive tab visibility and fixed dataset scope from that manifest instead of
  maintaining frontend-only mappings.
- Clearly label fixed-scope views such as DS3 Investigations and AML Network.

### P2-202: Operational status model

- Separate `ready`, `degraded`, `idle`, `stale` and `failed` consistently.
- Display last successful event, last successful evaluation and data age.
- Link every failed dependency to the relevant metric, log or runbook.

### P2-203: Frontend quality and performance

- Add error boundaries and request cancellation to every data-backed tab.
- Expand Playwright coverage to all tabs, empty/error states and both roles.
- Add accessibility checks and keyboard navigation coverage.
- Set bundle budgets and split the graph/chart bundles further where useful.

Exit criteria: every tab has loading, empty, error and success coverage; no
critical accessibility violations; initial application bundle stays within the
agreed budget.

## Phase 3 — Security and production hardening

Target: 1–2 weeks, in parallel with an infrastructure owner.

- Move secrets out of `.env` into an approved secret manager and rotate them.
- Introduce TLS at ingress and encrypted service connections where supported.
- Use separate least-privilege identities for API, processors, migrations,
  monitoring and backup jobs.
- Pin CI actions and container images by digest; generate SBOMs and verify
  signatures before promotion.
- Add rate limits, audit-log retention, session revocation and security-event
  alerts.
- Perform a threat review covering ingestion authentication, replay controls,
  evidence URLs, graph queries and administrative actions.

Exit criteria: no shared admin credentials in runtime services, no unresolved
critical vulnerability, and security/restore reviews are signed off.

## Phase 4 — ML enablement

Start only after authorized labeled data and point-in-time features exist.

- Build a leakage-safe feature pipeline and versioned feature definitions.
- Add model registry, approval workflow, reproducible training and evaluation.
- Run candidates in shadow mode before canary traffic.
- Monitor drift, calibration, precision/recall, false positives and segment
  fairness without exposing protected or identifying data.
- Keep deterministic rules available as a rollback path.

Exit criteria: a model is promoted only with signed data lineage, holdout
evidence, governance approval and a tested rollback.

## Target service levels for the pre-production gate

| Signal | Target |
| --- | --- |
| Required dependency readiness | 100% during acceptance and soak windows |
| Accepted-event loss | 0 |
| Duplicate canonical event rate | 0 |
| End-to-end payment processing latency | p95 under 5 seconds at the agreed load |
| Dashboard/API latency | p95 under 2 seconds |
| Kafka consumer lag | returns to zero after load and controlled faults |
| DLQ growth | zero for valid contracts; every invalid record explained |
| Unplanned processor restarts | 0 during the 24-hour soak |
| Data reconciliation | 100% of accepted events accounted for |

## Recommended execution order

1. P2-001 clean branch and acceptance baseline.
2. P2-002 blocking CI.
3. P2-003 observability and P2-004 soak/fault testing.
4. P2-101 through P2-104 data reliability and recovery.
5. P2-201 through P2-203 dashboard/operator improvements.
6. Phase 3 security hardening.
7. Phase 4 ML enablement only after its data prerequisites are approved.

