# P2 implementation plan (excluding CI/CD)

## 1. Goal and scope

This plan turns the current stable local platform into an observable,
reconcilable and operator-friendly pre-production system. It deliberately does
not include CI/CD work. Verification is performed with explicit local test and
runtime gates after every delivery unit.

The implementation must preserve these data boundaries:

- DS1, DS3 and DS4 are independent benchmark datasets.
- Investigations and AML Network remain fixed to DS3 until another dataset has
  equivalent alert and graph semantics.
- Live payment/transfer data is operational data and must never be mixed into a
  benchmark run or its metrics.
- Ground truth is available only to benchmark evaluation, never to runtime
  scoring logic.

## 2. Delivery method

Each numbered delivery unit below is implemented, verified and committed before
the next unit begins. A commit may contain only the files belonging to that
unit. The six currently modified Architecture/E2E/CSS files are reviewed and
closed first; they must not be mixed into later work.

Standard local acceptance matrix:

```bash
python -m pytest tests/unit -q
python -m pytest tests/data_quality -q
python -m pytest tests/integration -q
cd dashboard/frontend && npm run lint && npm test && npm run build
cd dashboard/frontend && npm run test:e2e
docker compose config --quiet
```

Not every unit needs the full matrix while being developed. The table for each
stage lists its minimum checks; the full matrix is mandatory at stage exit.

## 3. Target architecture added by P2

```text
Producer / replay
      |
      v
Versioned contract validator -----> DLQ with reason + trace_id + run_id
      |
      v
Kafka accepted offsets
      |
      +--------> Spark / benchmark processors --------> stores and alerts
      |                                                    |
      v                                                    v
Run control + reconciliation service <--------- observed counts / freshness
      |
      +--------> capability/status API --------> operator dashboard
      |
      +--------> Prometheus metrics -----------> Grafana / alerts
```

PostgreSQL is the control-plane system of record. Kafka remains the event
transport; ClickHouse, Neo4j and MinIO remain specialized serving stores.

## 4. Implementation sequence

### Stage 0 — Close the current baseline

Estimate: 0.5 day.

#### P2-0001 — Finalize the pending Architecture Map change

Scope:

- Review the existing changes in:
  `dashboard/frontend/e2e/dashboard.spec.js`,
  `dashboard/frontend/src/architectureContract.js`,
  `dashboard/frontend/src/architectureContract.test.js`,
  `dashboard/frontend/src/components/ArchitectureDiagram.jsx`,
  `dashboard/frontend/src/components/ArchitectureTab.jsx`, and
  `dashboard/frontend/src/index.css`.
- Confirm that the visual status contract matches `/api/health/ready`.
- Keep the scoped React Flow locators already added to the E2E test.

Minimum verification: frontend lint, unit, build and Playwright.

Commit boundary: `feat(dashboard): finalize live architecture status map`.

Exit gate: the working tree is clean and the existing acceptance baseline is
reproducible without uncommitted files.

### Stage 1 — Runtime observability and failure evidence

Estimate: 2–3 days.

#### P2-0101 — Persist processor heartbeats

Implementation:

- Add an additive PostgreSQL migration
  `dashboard/backend/sql/p2_runtime_observability.sql` with a
  `processor_heartbeats` table keyed by processor name and instance ID.
- Record status, last batch time, last success, last error, processed rows,
  restart/start identity and checkpoint age.
- Update `streaming/payment_processing.py`, `streaming/fraud_detection.py`,
  `kafka/consumers/benchmark_processor.py` and the graph processor to publish a
  heartbeat without blocking event processing.
- Expose heartbeat age and last error through a small backend service rather
  than querying runtime containers from the browser.

Tests: heartbeat upsert/idempotency unit tests and a stale-heartbeat integration
test.

Commit boundary: `feat(observability): persist processor heartbeats`.

#### P2-0102 — Export pipeline metrics

Implementation:

- Extend `dashboard/backend/main.py` metrics with processor availability,
  heartbeat age, accepted/processed/failed totals, batch duration, checkpoint
  age and data freshness.
- Add live-ingestion publish success/failure and last accepted-event timestamp
  if a metric is not already emitted by `ingestion/live_gateway`.
- Use bounded labels only: processor, topic, dataset and outcome. Never use
  event, account, payment or trace IDs as Prometheus labels.
- Extend `monitoring/prometheus/prometheus.yml` only where a new scrape target
  is actually required.

Tests: metric registration/unit tests and `/metrics` smoke test.

Commit boundary: `feat(observability): expose bounded pipeline metrics`.

#### P2-0103 — Add alerts, dashboard panels and runbook

Implementation:

- Extend `monitoring/prometheus/alerts.yml` for missing Spark workers, missing
  required applications, stale processor heartbeat, checkpoint age, Kafka lag,
  DLQ growth and stale accepted data.
- Extend `monitoring/grafana/dashboards/system_overview.json` with event rate,
  consumer lag, end-to-end age, processor restarts and DLQ panels.
- Add `docs/runbooks/pipeline-degraded.md` with symptom, diagnosis, recovery and
  data-integrity checks for each alert.
- Add direct runbook/metric references to Platform Health where practical.

Tests: `promtool check rules`, Prometheus config validation, frontend checks and
manual failed-heartbeat verification.

Commit boundary: `feat(observability): add pipeline alerts and runbook`.

#### P2-0104 — Automate soak and fault evidence

Implementation:

- Add `scripts/soak/run_soak.py` to sample readiness, rates, lag, freshness,
  restart counts, CPU/memory and DLQ offsets into `.runtime/soak/<run-id>/`.
- Add explicit fault scenarios for Kafka, Spark worker, PostgreSQL and Neo4j.
  Every scenario must target one named Compose service and restore it before
  continuing.
- Add a final integrity report covering accepted, processed, duplicated,
  missing and quarantined events.
- Run a two-hour gate first. Schedule a 24-hour gate only after all later data
  reliability stages are complete.

Tests: parser/unit tests plus a 10-minute smoke soak and one Spark-worker
restart scenario.

Commit boundary: `feat(operations): add soak and recovery evidence runner`.

Stage exit gate: a processor failure becomes visible within 60 seconds, the
runbook identifies the affected data path, and the smoke soak produces a
machine-readable integrity report.

### Stage 2 — Event contracts and durable run control

Estimate: 3–4 days.

#### P2-0201 — Consolidate versioned event contracts

Implementation:

- Keep the existing validators in `shared/payment_contract.py`,
  `shared/transfer_contract.py` and `shared/benchmark_contract.py` as the source
  of runtime normalization.
- Add machine-readable JSON Schemas under `shared/contracts/v1/` for payment,
  transfer, benchmark and alert envelopes.
- Add a shared `ContractError` containing contract, version, reason, trace ID,
  source topic and safe payload fingerprint.
- Standardize DLQ envelopes so all processors preserve the reason and original
  transport metadata without copying sensitive payloads into logs.
- Add a local compatibility command under `scripts/contracts/` that rejects
  breaking changes inside the same schema version.

Tests: valid/invalid fixtures, producer/consumer parity and compatibility
regression tests.

Commit boundary: `feat(contracts): publish versioned event schemas`.

#### P2-0202 — Add the run-control schema and API

Implementation:

- Add `dashboard/backend/sql/p2_run_control.sql` with:
  `pipeline_runs`, `pipeline_run_offsets`, `pipeline_run_counters` and
  `pipeline_run_events`.
- Use UUID run IDs and enforce the state machine:
  `CREATED -> RUNNING -> PAUSING -> PAUSED -> RUNNING -> CANCELLING ->
  CANCELLED`, with `COMPLETED` and `FAILED` as terminal states.
- Persist owner, source kind, dataset ID/version/hash, contract version,
  evaluator version, requested rate, offset range and timestamps.
- Add `dashboard/backend/api/runs.py` and a service layer with list/detail/create
  endpoints first. Mutation endpoints must use optimistic version checks and
  ADMIN authorization where they affect processing.
- Register the migration and router in `dashboard/backend/main.py`.

Tests: migration idempotency, state transitions, authorization, optimistic
locking and API contract tests.

Commit boundary: `feat(control-plane): add durable pipeline runs`.

#### P2-0203 — Make benchmark replay run-aware

Implementation:

- Update `kafka/producers/dataset_replay.py` to require or create a run ID and
  attach it to each benchmark envelope.
- Persist start/end offsets per partition and periodic accepted counters.
- Update `kafka/consumers/benchmark_processor.py` and
  `aml/graph/benchmark_graph.py` to store run ID with results and use it in
  idempotency keys.
- Add pause/cancel checks at bounded intervals. Resume must continue from saved
  offsets without reusing another run's metrics or graph namespace.
- Keep existing one-off command behavior through a wrapper that creates and
  completes a run automatically.

Tests: pause/resume, cancellation, retry after producer interruption, duplicate
delivery and two sequential runs of the same dataset.

Commit boundary: `feat(replay): make benchmark processing run-aware`.

Stage exit gate: every replay has one durable run record, deterministic offset
boundaries and isolated evaluation/graph outputs.

### Stage 3 — Reconciliation, quality and freshness

Estimate: 3–4 days.

#### P2-0301 — Persist run-level reconciliation

Implementation:

- Add `dashboard/backend/sql/p2_reconciliation.sql` with reconciliation checks
  and results keyed by run, store, metric and window.
- Refactor `scripts/reconcile_payment_events.py` into reusable services under
  `shared/reconciliation/`; retain the CLI as an operator entry point.
- Reconcile accepted Kafka offsets against PostgreSQL canonical events,
  ClickHouse facts, Neo4j edges, evaluations, alerts and DLQ records.
- Classify differences as pending, duplicate, missing, mismatched or
  quarantined. A pending record becomes missing only after its freshness SLA.
- Store sample IDs as bounded evidence, not unbounded result payloads.

Tests: exact match, eventual arrival, duplicate, missing, mismatched and DLQ
fixtures; Compose integration across PostgreSQL and ClickHouse.

Commit boundary: `feat(data-quality): persist run reconciliation`.

#### P2-0302 — Add freshness and quality API

Implementation:

- Add run summary/detail endpoints to `api/runs.py` and a dataset freshness
  endpoint to `api/datasets.py`.
- Return a shared status vocabulary: `ready`, `idle`, `running`, `stale`,
  `degraded`, `failed`, `completed` and `not_applicable`.
- Include `observed_at`, `last_success_at`, `data_age_seconds`, SLA threshold and
  reconciliation completeness in every operational response.
- Never infer “healthy” from an empty result; return `idle` or
  `not_applicable` with a reason.

Tests: boundary-time tests, empty dataset semantics, partial reconciliation and
status precedence.

Commit boundary: `feat(api): expose freshness and reconciliation status`.

#### P2-0303 — Build the Data Runs operator view

Implementation:

- Add a Data Runs section to the existing Data Sources tab rather than adding
  another global tab.
- Show state, owner, source, dataset version, progress, rate, lag, freshness,
  reconciliation and terminal reason.
- Add run detail with offsets, count flow and bounded discrepancy samples.
- Enable pause/resume/cancel only for allowed states and roles; require a clear
  confirmation for cancel.
- Add loading, empty, stale, partial and failed states with accessible labels.

Tests: frontend contract tests and Playwright for successful, stale, failed,
pause/resume and authorization states.

Commit boundary: `feat(dashboard): add data run control and reconciliation`.

Stage exit gate: 100% of accepted events in a completed test run are accounted
for as materialized or explicitly quarantined, and the dashboard identifies
stale/partial runs without inspecting logs.

### Stage 4 — Capability-driven dashboard and consistent status

Estimate: 2–3 days.

#### P2-0401 — Serve a capability manifest

Implementation:

- Add `dashboard/backend/services/capabilities.py` and
  `GET /api/capabilities`.
- Describe datasets, source kind, time semantics, supported tabs, graph/case
  support, ground-truth availability, allowed modes and required backend
  dependencies.
- Derive availability from declared contracts plus current readiness; keep the
  semantic capability separate from temporary runtime health.
- Version the response so the frontend can reject an unsupported manifest.

Tests: manifest schema, DS3-only Investigations/AML rules, readiness changes
and unknown-version behavior.

Commit boundary: `feat(api): publish dashboard capability manifest`.

#### P2-0402 — Replace frontend-only dataset routing

Implementation:

- Replace hard-coded capability decisions in
  `dashboard/frontend/src/datasetContextContract.js` with the manifest while
  retaining a safe bootstrap fallback.
- Keep Investigations and AML Network fixed to DS3 and remove irrelevant source
  filters from those views.
- Disable or hide unsupported tabs with an explicit reason; do not silently
  render zero-valued charts for unsupported data.
- Add a manifest loading/error boundary before rendering data-backed tabs.

Tests: unit tests for navigation matrix plus Playwright across live, DS1, DS3
and DS4 contexts.

Commit boundary: `feat(dashboard): drive navigation from capabilities`.

#### P2-0403 — Unify operational status presentation

Implementation:

- Introduce one frontend status component and token map for `ready`, `idle`,
  `running`, `stale`, `degraded`, `failed` and `not_applicable`.
- Use it in the header, Platform Health, Data Sources and run details.
- Display last successful event/evaluation, age and reason next to rates. In
  particular, `0 events/s` with a connected but idle source must read as idle,
  not failed.
- Add error boundaries and AbortController request cancellation to every
  data-backed tab.

Tests: status precedence/unit tests, aborted request test, visual Playwright
coverage for all status states and a keyboard/accessibility pass.

Commit boundary: `feat(dashboard): unify runtime status and data age`.

Stage exit gate: tab scope comes from the backend manifest, unsupported data is
never shown as zero, and all operator surfaces use the same status semantics.

### Stage 5 — Investigation and AML workflow

Estimate: 4–5 days.

#### P2-0501 — Complete investigation case records

Implementation:

- Extend the alert schema with case priority, disposition, due date, resolution
  code and closed metadata; preserve the existing audit log.
- Add append-only comments and evidence metadata tables. MinIO objects remain
  immutable; PostgreSQL stores ownership, hash, content type and audit events.
- Add case detail endpoints for comments, evidence, assignment and disposition
  using the existing optimistic locking model.
- Enforce role and ownership rules consistently for API and export.

Tests: state machine, concurrent update, evidence metadata, authorization and
audit completeness.

Commit boundary: `feat(investigations): add complete case records`.

#### P2-0502 — Upgrade the Investigation UI

Implementation:

- Split the queue and case detail so filters, pagination and selection have
  stable URLs.
- Add SLA/priority, timeline, notes, assignment, disposition and evidence
  sections.
- Link alert evidence to the source benchmark event and relevant AML subgraph.
- Preserve fixed DS3 scope and remove any dataset control from inside the tab.

Tests: frontend unit and Playwright for assign, investigate, comment, upload
metadata, resolve and conflict handling.

Commit boundary: `feat(dashboard): complete investigation workspace`.

#### P2-0503 — Add temporal AML graph evidence

Implementation:

- Store edge event time/relative step, run ID, event ID, amount and source
  provenance in the DS3 benchmark namespace.
- Add bounded graph queries for time window, hop count and risk threshold.
- Return path-level evidence with explicit distinction between participant-
  linked paths and source-row adjacency evidence.
- Add graph expansion controls and evidence links in AML Network without
  implying identities that PaySim does not provide.

Tests: temporal-window graph fixtures, namespace isolation, query bounds and
Playwright graph-detail coverage.

Commit boundary: `feat(aml): add temporal graph evidence`.

Stage exit gate: an investigator can move from an alert to an auditable case,
source event and bounded graph evidence without changing dataset context.

### Stage 6 — Retention, recovery and security hardening

Estimate: 4–6 days, depending on selected secret and object-storage solutions.

#### P2-0601 — Define and enforce retention

Implementation:

- Add `docs/retention-policy.md` covering Kafka topics, DLQs, PostgreSQL audit
  and run data, ClickHouse events, Neo4j relationships, MinIO evidence and Spark
  checkpoints.
- Add safe, dry-run-first cleanup commands scoped by explicit cutoff and source.
- Protect active/paused runs, open cases and referenced evidence from cleanup.
- Record every cleanup execution and count in the control plane.

Tests: retention boundary, legal-hold/open-case protection, dry-run parity and
idempotency.

Commit boundary: `feat(governance): add retention controls`.

#### P2-0602 — Rehearse multi-store recovery

Implementation:

- Extend the existing PostgreSQL recovery rehearsal to ClickHouse, Neo4j,
  MinIO, Kafka configuration/offset evidence and Spark checkpoints.
- Define restore order and an integrity check that uses the reconciliation
  service after recovery.
- Store only reports and manifests in `.runtime/backups`; never commit backups
  or credentials.

Tests: isolated restore rehearsal for each stateful dependency and one ordered
  end-to-end rehearsal.

Commit boundary: `feat(recovery): rehearse multi-store restore`.

#### P2-0603 — Harden runtime identities and ingress

Implementation:

- Replace shared service credentials with separate least-privilege identities
  for API, processors, migrations, monitoring and backup.
- Move secrets to the approved local/pre-production secret provider and rotate
  the current values.
- Add TLS at ingress and encrypted service connections where supported.
- Add API rate limits, session revocation, audit retention and security-event
  metrics.
- Pin runtime container images by digest and document upgrade procedure.

Tests: permission-denial tests, expired/revoked session tests, TLS checks,
secret-absence scan and restore with least-privilege identities.

Commit boundary: split into one commit per identity/secrets, transport security
and session/rate-limit subpart; do not combine all security changes in one
commit.

Stage exit gate: each stateful service has a verified restore report, runtime
services do not share admin credentials, and retention cannot delete active
run or open-case evidence.

### Stage 7 — ML shadow evaluation (conditional)

Estimate: 4–6 days after labeled, authorized data and point-in-time features
are approved. This stage must not begin merely because earlier engineering work
is complete.

#### P2-0701 — Version point-in-time features and model artifacts

- Define leakage-safe features with event-time joins and dataset lineage.
- Record training/holdout hashes, feature schema, model hash, metrics and owner
  in the existing model-candidate registry.
- Make deterministic rules the mandatory fallback.

Commit boundary: `feat(ml): version point-in-time model inputs`.

#### P2-0702 — Run shadow scoring

- Publish candidate scores to a shadow-only sink; they must not create or close
  operational cases.
- Compare calibration, precision/recall, false positives, drift and segment
  behavior against the deterministic baseline.
- Add a dashboard view clearly labeled Shadow / Not production eligible.

Commit boundary: `feat(ml): add governed shadow evaluation`.

Stage exit gate: a candidate can be reproduced from signed lineage evidence and
disabled without affecting the deterministic pipeline.

## 5. Calendar and dependency plan

| Week | Delivery units | Required predecessor | Demonstrable result |
| --- | --- | --- | --- |
| 1 | P2-0001, P2-0101–P2-0104 | Current stable stack | Failures, lag and freshness visible; smoke soak report |
| 2 | P2-0201–P2-0203 | Observability | Versioned contracts and durable replay runs |
| 3 | P2-0301–P2-0303 | Run IDs and offsets | Run-level reconciliation in API and dashboard |
| 4 | P2-0401–P2-0403 | Stable status API | Capability-driven tabs and consistent status UX |
| 5 | P2-0501–P2-0503 | Run/evidence identity | Auditable investigations and temporal AML evidence |
| 6 | P2-0601–P2-0603 | Reconciliation | Retention, recovery and security evidence |
| After approval | P2-0701–P2-0702 | Authorized labels/features | Governed shadow model only |

The estimates assume one primary implementer and uninterrupted access to the
local Compose environment. Security provider selection and the 24-hour soak are
elapsed-time risks and should not be hidden inside coding estimates.

## 6. Global acceptance criteria

P2 is complete, excluding the conditional ML stage, when all of the following
are true:

1. Every processor and required dependency has a current, queryable health and
   freshness signal.
2. Every accepted event in a completed run is materialized or explicitly
   quarantined; duplicates and missing records are zero at the final gate.
3. Replays can pause, resume and cancel without crossing run or dataset
   boundaries.
4. Dashboard tabs and charts are enabled by backend capabilities, not static
   frontend assumptions.
5. `0 events/s` is explained as idle, stale or failed using evidence and age.
6. DS3 Investigations and AML Network provide an auditable path from case to
   source event and graph evidence.
7. The two-hour and 24-hour soak reports meet the targets in
   `docs/p2-upgrade-roadmap.md`.
8. Retention and restore procedures have recorded, reproducible evidence.
9. The full local acceptance matrix passes from a clean working tree.

## 7. First execution batch

Start with exactly these commits, in order:

1. `feat(dashboard): finalize live architecture status map`
2. `feat(observability): persist processor heartbeats`
3. `feat(observability): expose bounded pipeline metrics`
4. `feat(observability): add pipeline alerts and runbook`
5. `feat(operations): add soak and recovery evidence runner`

After commit 5, run the 10-minute smoke soak and review its report before
starting event-contract or run-control schema changes.
