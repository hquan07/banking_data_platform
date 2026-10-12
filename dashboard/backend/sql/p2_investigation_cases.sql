-- Complete, auditable investigation records. Additive and idempotent.

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS priority VARCHAR(8) NOT NULL DEFAULT 'P3';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS disposition VARCHAR(40);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolution_code VARCHAR(60);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS closed_by INT REFERENCES users(id);

ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_priority_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_priority_check
    CHECK (priority IN ('P1', 'P2', 'P3', 'P4'));
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_disposition_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_disposition_check
    CHECK (disposition IS NULL OR disposition IN (
        'CONFIRMED_FRAUD', 'FALSE_POSITIVE', 'DUPLICATE',
        'NO_ACTION', 'REFERRED'
    ));
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_resolution_code_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_resolution_code_check
    CHECK (resolution_code IS NULL OR resolution_code IN (
        'FRAUD_CONFIRMED', 'FALSE_POSITIVE', 'DUPLICATE_CASE',
        'INSUFFICIENT_EVIDENCE', 'REFERRED_TO_COMPLIANCE'
    ));
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_due_after_creation_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_due_after_creation_check
    CHECK (due_at IS NULL OR due_at >= created_at);

CREATE INDEX IF NOT EXISTS ix_alerts_priority_due
    ON alerts (priority, due_at) WHERE status IN ('PENDING', 'INVESTIGATING');
CREATE INDEX IF NOT EXISTS ix_alerts_closed_at ON alerts (closed_at DESC)
    WHERE closed_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS alert_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES alerts(alert_id) ON DELETE CASCADE,
    author_user_id INT NOT NULL REFERENCES users(id),
    body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_comments_alert_created
    ON alert_comments (alert_id, created_at, comment_id);

CREATE INDEX IF NOT EXISTS ix_evidence_files_alert_created
    ON evidence_files (alert_id, created_at, evidence_id);

COMMENT ON TABLE alert_comments IS
    'Append-only case comments; the application exposes INSERT and read operations only.';
COMMENT ON COLUMN evidence_files.checksum_sha256 IS
    'Client-computed SHA-256 verified against immutable object metadata at completion.';
