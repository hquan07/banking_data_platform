-- Additive DQ run history. Rollback: retain this table for audit; stop readers first.
CREATE TABLE IF NOT EXISTS dq_run_results (
    run_id VARCHAR(120) PRIMARY KEY,
    source_path TEXT NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    invalid_count BIGINT NOT NULL CHECK (invalid_count >= 0),
    duplicate_rate DOUBLE PRECISION NOT NULL CHECK (duplicate_rate BETWEEN 0 AND 1),
    success BOOLEAN NOT NULL,
    checks JSONB NOT NULL,
    quarantine_path TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_dq_run_results_checked_at ON dq_run_results (checked_at DESC);
