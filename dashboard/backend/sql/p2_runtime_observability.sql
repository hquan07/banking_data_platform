-- Durable processor liveness and latest-batch evidence.
-- Additive and idempotent: processors upsert only their own instance row.

CREATE TABLE IF NOT EXISTS processor_heartbeats (
    processor_name VARCHAR(80) NOT NULL,
    instance_id VARCHAR(160) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('starting', 'running', 'failed', 'stopped')),
    started_at TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL,
    last_batch_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_error TEXT,
    processed_rows BIGINT NOT NULL DEFAULT 0 CHECK (processed_rows >= 0),
    checkpoint_age_seconds DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (processor_name, instance_id)
);

CREATE INDEX IF NOT EXISTS ix_processor_heartbeats_latest
    ON processor_heartbeats (processor_name, heartbeat_at DESC);
