# DS3 PaySim controlled replay — 2026-10-09

## Scope

This run extends the original 1,000-event canary without starting an
unbounded full-source replay. The source remains the synthetic PaySim dataset
documented in `ds3-paysim-canary.md`.

Replay configuration:

- start row: 1,000 (zero-based)
- maximum events: 10,000
- source row range: 1,000–10,999
- pacing: disabled for the controlled local run
- published: 10,000
- rejected by the producer: 0

## Reconciliation

Both consumer groups reached zero lag before the sink counts were captured.

| Check | Result |
| --- | ---: |
| PostgreSQL DS3 events, cumulative | 11,000 |
| Ground-truth fraud rows, cumulative | 72 |
| `benchmark-rules-v2` evaluations, cumulative | 11,000 |
| `benchmark-rules-v1` evaluations retained from the canary | 1,000 |
| `BALANCE_MISMATCH` alerts, cumulative | 417 |
| `ZERO_DRAIN` alerts, cumulative | 65 |
| `TRANSFER_CASHOUT_SEQUENCE` alerts, new run | 31 |
| Neo4j `BenchmarkAccount` nodes, cumulative | 18,247 |
| Neo4j `BENCHMARK_TRANSACTION` relationships, cumulative | 11,000 |
| Neo4j source sequences, cumulative | 35 |
| `benchmark-processor-v2` lag | 0 |
| `benchmark-graph-v1` lag | 0 |
| `benchmark-events-dlq` end offsets, all partitions | 0 |

The graph contains 35 source sequences while this run emitted 31 sequence
alerts. The four earlier canary sequences were backfilled into Neo4j after the
sequence definition was corrected; alerts were intentionally not generated
retroactively.

## Decision

The bounded 10,000-event increment passed producer, Kafka, PostgreSQL and
Neo4j reconciliation with no DLQ records. This is a functional capacity check,
not a formal throughput or latency benchmark: elapsed time and per-event
latency were not captured by an instrumented harness.

A full 6.36-million-row replay remains an explicit operator decision because
it materially increases Kafka retention, database volume and dashboard query
cost. At this checkpoint, the 11,000-event DS3 corpus was sufficient for the
demo analytics, rule evaluation and graph views; later performance runs are
recorded separately.
