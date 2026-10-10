# DS3 PaySim 50 EPS performance acceptance — 2026-10-10

## Scope and gates

This bounded run validates the local benchmark replay path after batching
Neo4j writes. It is a demo capacity check, not a production SLA.

- source row range: 76,501–91,500 (zero-based)
- events: 15,000
- target rate: 50 events/second for 5 minutes
- active-rate gate: at least 47.5 events/second (95% of target)
- peak-lag gate: at most 100 records for every consumer group
- drain timeout: 300 seconds
- API samples: 20 sequential requests per endpoint

The raw machine-readable report is generated locally at
`.runtime/performance/ds3-50eps-15k-batched.json` and is excluded from Git.

## Result

`PASS`.

| Check | Result |
| --- | ---: |
| Active replay duration | 300.002 seconds |
| Observed active rate | 50.000 events/second |
| Producer orchestration duration | 311.586 seconds |
| Published / rejected | 15,000 / 0 |
| `benchmark-processor-v2` peak lag | 53 |
| `benchmark-graph-v1` peak lag | 6 |
| Final lag, both groups | 0 |
| Drain time | 3.468 seconds |
| DLQ delta | 0 |
| PostgreSQL event delta | 15,000 |
| PostgreSQL evaluation delta | 15,000 |
| Alert delta | 564 |

The pre-run and post-run DS3 event/evaluation counts were 76,501 and 91,501.
After reconciliation, Neo4j contained 138,851 `BenchmarkAccount` nodes and
91,501 `BENCHMARK_TRANSACTION` relationships.

## API latency after drain

All 140 requests succeeded. Every observed maximum remained below the plan's
two-second ceiling.

| Endpoint | p95 | p99 | Maximum |
| --- | ---: | ---: | ---: |
| `/api/health/ready` | 7.454 ms | 8.523 ms | 8.790 ms |
| `/api/datasets/status` | 21.625 ms | 21.658 ms | 21.666 ms |
| `/api/datasets/performance` | 68.520 ms | 73.126 ms | 74.278 ms |
| `/api/datasets/balance-anomalies` | 627.297 ms | 760.226 ms | 793.458 ms |
| `/api/datasets/behavior-distributions` | 12.739 ms | 13.658 ms | 13.888 ms |
| `/api/graph/money-flow` | 78.166 ms | 83.232 ms | 84.499 ms |
| `/api/graph/fraud-sequences` | 245.082 ms | 253.885 ms | 256.085 ms |

## Capacity conclusion

The local demo stack sustains the scoped 50 EPS PaySim replay while keeping
both PostgreSQL and Neo4j consumer lag below 100 and reconciling without DLQ
records. The earlier one-transaction-per-event graph implementation exceeded
the lag gate; batching Kafka polls and Neo4j `UNWIND` writes reduced graph peak
lag from 6,774 to 6 and drain time from 254.023 seconds to 3.468 seconds.

This result applies only to the current machine, synthetic PaySim source,
15,000-event window and local Compose topology. It does not establish sustained
production capacity or performance on real banking traffic.
