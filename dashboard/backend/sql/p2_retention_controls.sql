-- Auditable, dry-run-first retention controls for source-scoped cleanup.

ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS legal_hold BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS legal_hold_reason VARCHAR(500);
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS legal_hold_at TIMESTAMPTZ;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS legal_hold_by INT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS retention_purged_at TIMESTAMPTZ;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS retention_execution_id UUID;

ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_legal_hold_reason_check;
ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_legal_hold_reason_check CHECK (
    (legal_hold = FALSE AND legal_hold_reason IS NULL AND legal_hold_at IS NULL)
    OR
    (legal_hold = TRUE AND legal_hold_reason IS NOT NULL AND legal_hold_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_retention_candidates
    ON pipeline_runs (dataset_id, completed_at, cancelled_at, failed_at)
    WHERE legal_hold = FALSE AND retention_purged_at IS NULL
      AND status IN ('COMPLETED', 'CANCELLED', 'FAILED');

CREATE TABLE IF NOT EXISTS retention_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode VARCHAR(12) NOT NULL CHECK (mode IN ('DRY_RUN', 'APPLY')),
    status VARCHAR(16) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'REJECTED')),
    source VARCHAR(64) NOT NULL CHECK (source ~ '^[a-z0-9_]+$'),
    cutoff_at TIMESTAMPTZ NOT NULL,
    requested_by VARCHAR(120) NOT NULL,
    actor_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    approved_dry_run_id UUID REFERENCES retention_executions(execution_id) ON DELETE RESTRICT,
    candidate_fingerprint CHAR(64),
    candidate_run_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message VARCHAR(1000),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    CHECK (mode = 'DRY_RUN' OR approved_dry_run_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_retention_executions_scope
    ON retention_executions (source, cutoff_at DESC, started_at DESC);

CREATE TABLE IF NOT EXISTS retention_execution_items (
    execution_id UUID NOT NULL REFERENCES retention_executions(execution_id) ON DELETE RESTRICT,
    store VARCHAR(32) NOT NULL,
    candidate_count BIGINT NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
    protected_count BIGINT NOT NULL DEFAULT 0 CHECK (protected_count >= 0),
    deleted_count BIGINT NOT NULL DEFAULT 0 CHECK (deleted_count >= 0),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (execution_id, store)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_retention_execution_fkey'
    ) THEN
        ALTER TABLE pipeline_runs
            ADD CONSTRAINT pipeline_runs_retention_execution_fkey
            FOREIGN KEY (retention_execution_id)
            REFERENCES retention_executions(execution_id) ON DELETE RESTRICT;
    END IF;
END $$;

COMMENT ON TABLE retention_executions IS
    'Immutable cleanup execution scope and outcome; APPLY must approve a matching DRY_RUN.';
COMMENT ON COLUMN pipeline_runs.retention_purged_at IS
    'Materialized run data was purged; control-plane metadata and audit remain.';
