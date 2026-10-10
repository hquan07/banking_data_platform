# P1 end-to-end acceptance — 2026-10-10

## Scope

The full live integration suite was executed against the local Docker Compose
stack with `RUN_LIVE_E2E=1`. The suite uses unique run identifiers and cleans
up the records it owns where applicable.

The following paths passed:

1. payment event delivery to PostgreSQL and ClickHouse plus fraud-topic output;
2. malformed and unsupported payment events routed to the DLQ;
3. approved payment retry returned to the primary topic;
4. alert case transitions, optimistic-version rejection and evidence upload;
5. role revocation and authorized case search;
6. Redis velocity deduplication and late-event exclusion;
7. Neo4j cycle detection and low-amount false-positive control;
8. MinIO evidence round trip and presigned download.

## Result

`PASS` — 8 tests passed in 77.60 seconds.

The supporting regression checks also passed:

- Python unit and data-quality suite: 60 passed, 3 intentionally skipped;
- frontend stream-contract test: 1 passed;
- frontend production build: completed successfully.

The six warnings emitted during the live suite come from botocore's use of the
deprecated naive `datetime.utcnow()` API. They do not represent application
test failures and should be removed by a future dependency refresh.

## Boundary

This run validates the current local Compose topology and P1 application
contracts. It does not replace a longer soak test, backup/restore rehearsal,
security review or validation against authorized live banking sources.
