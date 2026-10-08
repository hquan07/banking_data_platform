# Data source status

Runtime-generated transactions, alerts, transfer scenarios, synthetic training
rows and canned API responses have been removed. The dashboard now shows empty
states when no events or records exist. The API returns a service error when a
required datastore is unavailable instead of substituting sample values.

No public dataset adapter is connected yet. Kafka consumers, the transfer
contract, fraud rules, alert workflow and graph processing remain available,
but they require events from an external source before the charts and case
lists contain data. `APP_MODE` accepts `integration` and `production`; there is
no runtime demo mode or `ENABLE_MOCK_DATA` switch.

Static analytics panels that had no data-backed API have been removed. The
Architecture Map remains and identifies the payment and transfer sources as
unconfigured. A dataset replay adapter should add source identity and run
provenance without putting ground-truth labels into live scoring messages.

The clean-up changes application code and documentation only. It does not
delete database rows, Kafka records, checkpoints, Neo4j nodes, MinIO objects or
other mounted-volume contents. Those records need a provenance review before
any targeted purge.
