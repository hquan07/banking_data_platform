# benchmark-events v1

Kafka topic (introduced by the replay phase): `benchmark-events`. Kafka key:
`event_id`.

The contract represents four independent public benchmarks without pretending
that they share customers, accounts, currencies or calendar timelines.

Required envelope fields:

- `schema_version`: integer `1`
- `dataset_id`: one of `ds1_creditcard`, `ds2_ieee_cis`, `ds3_paysim`,
  `ds4_baf`
- `event_id`, `trace_id`, `source_row_id`: stable, nonempty identifiers
- `event_type`: source-specific canonical type
- `event_time`: relative value/unit with a null origin
- `payload`: source-specific normalized fields and feature groups
- `ground_truth.is_fraud`: evaluation label, never an inference input
- `provenance.source_file` and `provenance.source_kind`

No mapper may fabricate a customer, account, card, currency, location or
wall-clock timestamp that the source does not provide. In particular, DS1 PCA
features must not be hashed into pseudo-identities, and IEEE-CIS address codes
must not be rendered as geographic coordinates.

Ground truth is carried so offline evaluation and dashboard confusion matrices
can be reproduced. Scoring consumers must remove the `ground_truth` object
before creating their feature vector.
