CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(16) NOT NULL DEFAULT 'CREATED'
        CHECK (status IN ('CREATED', 'RUNNING', 'PAUSING', 'PAUSED',
                          'CANCELLING', 'CANCELLED', 'COMPLETED', 'FAILED')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    source_kind VARCHAR(32) NOT NULL
        CHECK (source_kind IN ('BENCHMARK_REPLAY', 'LIVE_INGESTION', 'MANUAL_REPLAY')),
    dataset_id VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(120) NOT NULL,
    dataset_hash CHAR(64) NOT NULL CHECK (dataset_hash ~ '^[a-f0-9]{64}$'),
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    evaluator_version VARCHAR(120) NOT NULL,
    requested_rate NUMERIC(12, 3) NOT NULL CHECK (requested_rate > 0),
    requested_start_offset BIGINT CHECK (requested_start_offset >= 0),
    requested_end_offset BIGINT CHECK (requested_end_offset >= requested_start_offset),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS pipeline_runs_status_created_idx
    ON pipeline_runs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS pipeline_runs_dataset_created_idx
    ON pipeline_runs (dataset_id, created_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_run_offsets (
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    topic VARCHAR(249) NOT NULL,
    partition INTEGER NOT NULL CHECK (partition >= 0),
    start_offset BIGINT NOT NULL CHECK (start_offset >= 0),
    end_offset BIGINT CHECK (end_offset >= start_offset),
    current_offset BIGINT CHECK (current_offset >= start_offset),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, topic, partition)
);

CREATE TABLE IF NOT EXISTS pipeline_run_counters (
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    counter_name VARCHAR(64) NOT NULL,
    counter_value BIGINT NOT NULL DEFAULT 0 CHECK (counter_value >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, counter_name)
);

CREATE TABLE IF NOT EXISTS pipeline_run_events (
    event_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    event_type VARCHAR(32) NOT NULL,
    old_status VARCHAR(16),
    new_status VARCHAR(16),
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS pipeline_run_events_run_created_idx
    ON pipeline_run_events (run_id, created_at, event_id);

CREATE OR REPLACE FUNCTION enforce_pipeline_run_state_transition()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;
    IF NOT (
        (OLD.status = 'CREATED' AND NEW.status IN ('RUNNING', 'FAILED')) OR
        (OLD.status = 'RUNNING' AND NEW.status IN ('PAUSING', 'CANCELLING', 'COMPLETED', 'FAILED')) OR
        (OLD.status = 'PAUSING' AND NEW.status IN ('PAUSED', 'CANCELLING', 'FAILED')) OR
        (OLD.status = 'PAUSED' AND NEW.status IN ('RUNNING', 'CANCELLING', 'FAILED')) OR
        (OLD.status = 'CANCELLING' AND NEW.status IN ('CANCELLED', 'FAILED'))
    ) THEN
        RAISE EXCEPTION 'invalid pipeline run transition: % -> %', OLD.status, NEW.status
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pipeline_run_state_transition ON pipeline_runs;
CREATE TRIGGER pipeline_run_state_transition
BEFORE UPDATE OF status ON pipeline_runs
FOR EACH ROW EXECUTE FUNCTION enforce_pipeline_run_state_transition();
