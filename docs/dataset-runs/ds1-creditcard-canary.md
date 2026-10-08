# DS1 credit-card canary — 2026-10-09

## Scope

This run verifies DS1 ingestion independently from the rejected offline model
candidate documented in `ds1-creditcard-baseline.md`.

Replay configuration:

- start row: 0
- maximum events: 1,000
- pacing: disabled for the local canary
- published: 1,000
- rejected by the producer: 0

## Reconciliation

Both benchmark consumer groups reached zero lag before counts were captured.

| Check | Result |
| --- | ---: |
| PostgreSQL DS1 events | 1,000 |
| Ground-truth fraud rows | 2 |
| `benchmark-rules-v2` evaluations | 1,000 |
| Predicted fraud | 0 |
| DS1 alerts | 0 |
| `benchmark-processor-v2` lag | 0 |
| `benchmark-graph-v1` lag | 0 |
| `benchmark-events-dlq` end offsets, all partitions | 0 |

Neo4j relationships are not expected for DS1 because the source has no account
or card identifiers and does not represent linked transfers.

## Decision

The ingestion canary passed. DS1 remains fail-closed in the streaming evaluator:
the offline Isolation Forest candidate did not meet its precision/recall gate,
so replayed labels are retained for evaluation and analytics but are never used
as rule input or converted directly into alerts.
