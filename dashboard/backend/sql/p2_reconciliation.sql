-- Durable, bounded reconciliation evidence for each pipeline run and source window.
CREATE TABLE IF NOT EXISTS pipeline_reconciliation_checks (
    check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    store VARCHAR(32) NOT NULL CHECK (
        store IN ('KAFKA', 'POSTGRESQL', 'CLICKHOUSE', 'NEO4J', 'EVALUATIONS', 'ALERTS', 'DLQ')
    ),
    metric VARCHAR(80) NOT NULL,
    window_key VARCHAR(500) NOT NULL,
    expected_count BIGINT NOT NULL CHECK (expected_count >= 0),
    freshness_sla_seconds INTEGER NOT NULL CHECK (freshness_sla_seconds >= 0),
    due_at TIMESTAMPTZ NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, store, metric, window_key)
);

CREATE TABLE IF NOT EXISTS pipeline_reconciliation_results (
    check_id UUID NOT NULL REFERENCES pipeline_reconciliation_checks(check_id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    store VARCHAR(32) NOT NULL CHECK (
        store IN ('KAFKA', 'POSTGRESQL', 'CLICKHOUSE', 'NEO4J', 'EVALUATIONS', 'ALERTS', 'DLQ')
    ),
    metric VARCHAR(80) NOT NULL,
    window_key VARCHAR(500) NOT NULL,
    classification VARCHAR(24) NOT NULL CHECK (
        classification IN ('EXACT', 'PENDING', 'DUPLICATE', 'MISSING', 'MISMATCHED', 'QUARANTINED')
    ),
    expected_count BIGINT NOT NULL CHECK (expected_count >= 0),
    actual_count BIGINT NOT NULL CHECK (actual_count >= 0),
    discrepancy_count BIGINT NOT NULL CHECK (discrepancy_count >= 0),
    sample_ids JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (
        jsonb_typeof(sample_ids) = 'array' AND jsonb_array_length(sample_ids) <= 25
    ),
    observed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (check_id, classification),
    UNIQUE (run_id, store, metric, window_key, classification)
);

ALTER TABLE pipeline_reconciliation_results
    DROP CONSTRAINT IF EXISTS pipeline_reconciliation_results_store_check;
ALTER TABLE pipeline_reconciliation_results
    ADD CONSTRAINT pipeline_reconciliation_results_store_check CHECK (
        store IN ('KAFKA', 'POSTGRESQL', 'CLICKHOUSE', 'NEO4J', 'EVALUATIONS', 'ALERTS', 'DLQ')
    );

CREATE INDEX IF NOT EXISTS ix_reconciliation_checks_run
    ON pipeline_reconciliation_checks (run_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_reconciliation_results_run_classification
    ON pipeline_reconciliation_results (run_id, classification, observed_at DESC);
