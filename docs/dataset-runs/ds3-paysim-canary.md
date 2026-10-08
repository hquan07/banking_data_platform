# DS3 PaySim canary — 2026-10-08

## Source verification

- Kaggle source: `ealaxi/paysim1`
- License reported by Kaggle CLI: `CC-BY-SA-4.0`
- Provenance: synthetic mobile-money simulation
- Local file: `datasets/raw/paysim/PS_20174392719_1491204439457_log.csv`
  (excluded from Git)
- SHA-256: `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`
- Rows: 6,362,620
- Columns: 11
- Transaction types: 5
- Missing required columns: none
- Observed fraud prevalence: 0.1290820%

## Kafka canary

Replay configuration:

- start row: 0
- maximum events: 1,000
- pacing: disabled for the local canary
- published: 1,000
- rejected to DLQ: 0

Downstream reconciliation after both consumer groups reached zero lag:

| Sink | Result |
| --- | ---: |
| PostgreSQL `benchmark_events` | 1,000 |
| PostgreSQL `benchmark_evaluations` | 1,000 |
| Neo4j `BenchmarkAccount` nodes | 1,597 |
| Neo4j `BENCHMARK_TRANSACTION` relationships | 1,000 |
| `benchmark-processor-v1` lag | 0 |
| `benchmark-graph-v1` lag | 0 |

## Decision

The canary passed. A full 6.36-million-row replay was not started automatically;
it is an operator workload decision because it changes Kafka retention volume,
database size and dashboard query cost. The source remains clearly labeled
synthetic in events, graph nodes and UI provenance.

## Full-source sequence audit

A read-only chunked scan of all 6,362,620 source rows found 8,213 fraud-labeled
rows: 4,097 `TRANSFER` and 4,116 `CASH_OUT`. There are 4,075 adjacent
`TRANSFER` → `CASH_OUT` pairs with the same relative step and amount, but zero
pairs where `TRANSFER.nameDest` equals `CASH_OUT.nameOrig` under the proposed
24-step and ±20% amount criteria.

The original mule-chain assumption is therefore rejected for this dataset.
The graph pipeline records `TRANSFER_CASHOUT_SEQUENCE` using adjacent source
rows, equal step and equal amount, and explicitly marks `participant_linked`
as false. It does not create a fabricated victim → mule → exit relationship.
