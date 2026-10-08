-- Source-safe storage for independent public fraud benchmarks.

CREATE TABLE IF NOT EXISTS benchmark_events (
    event_id VARCHAR(120) PRIMARY KEY,
    trace_id VARCHAR(120) NOT NULL,
    dataset_id VARCHAR(40) NOT NULL,
    source_row_id VARCHAR(120) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    relative_time_value DOUBLE PRECISION NOT NULL,
    relative_time_unit VARCHAR(20) NOT NULL,
    payload JSONB NOT NULL,
    ground_truth_is_fraud BOOLEAN NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    source_kind VARCHAR(50) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, source_row_id)
);

CREATE INDEX IF NOT EXISTS ix_benchmark_events_dataset
    ON benchmark_events (dataset_id, ingested_at DESC);
CREATE INDEX IF NOT EXISTS ix_benchmark_events_type
    ON benchmark_events (event_type, ingested_at DESC);

CREATE TABLE IF NOT EXISTS benchmark_evaluations (
    evaluation_id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(120) NOT NULL REFERENCES benchmark_events(event_id),
    dataset_id VARCHAR(40) NOT NULL,
    evaluator_version VARCHAR(80) NOT NULL,
    predicted_fraud BOOLEAN NOT NULL,
    max_score NUMERIC(5, 2) NOT NULL CHECK (max_score >= 0 AND max_score <= 100),
    triggered_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, evaluator_version)
);

CREATE INDEX IF NOT EXISTS ix_benchmark_evaluations_dataset
    ON benchmark_evaluations (dataset_id, evaluator_version);

ALTER TABLE alerts ALTER COLUMN account_id DROP NOT NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS entity_id VARCHAR(120);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS entity_type VARCHAR(40);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS dataset_id VARCHAR(40);
UPDATE alerts SET entity_id = account_id, entity_type = 'account'
WHERE entity_id IS NULL AND account_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_alerts_entity ON alerts (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_alerts_dataset ON alerts (dataset_id, created_at DESC);

INSERT INTO rules (name, description, threshold, window_seconds, max_count)
VALUES (
    'TRANSFER_CASHOUT_SEQUENCE',
    'PaySim benchmark: adjacent TRANSFER and CASH_OUT source rows with equal step and amount; participants are not linked',
    0.80,
    1,
    1
)
ON CONFLICT (name) DO NOTHING;

UPDATE rules
SET is_active = FALSE,
    description = 'Deprecated: PaySim participant identifiers do not link TRANSFER destinations to CASH_OUT origins',
    updated_at = NOW()
WHERE name = 'TRANSFER_CASHOUT_CHAIN';
