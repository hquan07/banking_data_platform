# Transfer graph and AML cycles

The `graph_processor` consumes version-1 `transfer-events` keyed by
`from_account_id`. Payment events do **not** include a destination account and
must not be treated as transfers. An upstream core-banking transfer publisher
must supply `event_id`, `trace_id`, `from_account_id`, `to_account_id`, positive
`amount`, uppercase three-letter `currency`, and a timezone-aware `timestamp`.
The contract is enforced in `shared/transfer_contract.py`.

No transfer event source is currently connected. The graph remains empty until
a dataset replay adapter or an upstream transfer publisher sends events that
meet the v1 contract.

Neo4j account edges are merged by source event ID and carry amount, currency,
UTC event time, trace ID, Kafka topic/partition/offset. Customer, account and
merchant node IDs have uniqueness constraints. Cycles of 3–5 distinct accounts
are flagged only if every edge has the same currency, occurred within one hour
before the closing edge, and meets `GRAPH_MIN_TRANSFER_AMOUNT` (default 1000).
The deterministic cycle alert is published to `aml-events`; the dashboard's
idempotent consumer stores it as a case. Invalid transfer records go to
`transfer-events-dlq` with source coordinates.

Kafka offsets are committed only after graph persistence and alert publication.
If Neo4j is unavailable, the container restarts and replays from its committed
offset; repeated edges and alerts are idempotent. Keep Kafka retention longer
than the worst expected outage (currently seven days). Before replaying an
invalid record, correct its payload while retaining its original event ID;
publish to `transfer-events` with the source account as key. The DLQ is never
replayed automatically.
