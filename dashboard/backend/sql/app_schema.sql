-- Application schema for the dashboard and alert lifecycle.
-- Safe to run repeatedly on an existing database.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'ANALYST', 'OPERATOR')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(120),
    payment_id VARCHAR(50),
    account_id VARCHAR(50) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'
        CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    decision VARCHAR(30) NOT NULL DEFAULT 'REVIEW',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'INVESTIGATING', 'RESOLVED', 'IGNORED')),
    xai_explanation TEXT,
    notes TEXT,
    evidence_file_url VARCHAR(500),
    assignee_id INT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS event_id VARCHAR(120);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS payment_id VARCHAR(50);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS decision VARCHAR(30) NOT NULL DEFAULT 'REVIEW';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS is_active BOOLEAN;

CREATE TABLE IF NOT EXISTS rules (
    rule_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    threshold NUMERIC(18, 2) NOT NULL DEFAULT 10000,
    window_seconds INT NOT NULL DEFAULT 60 CHECK (window_seconds > 0),
    max_count INT NOT NULL DEFAULT 3 CHECK (max_count > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO rules (name, description, threshold, window_seconds, max_count)
VALUES
    ('LARGE_TRANSACTION', 'Giao dịch vượt ngưỡng giá trị', 10000, 60, 1),
    ('HIGH_VELOCITY', 'Nhiều giao dịch trong cửa sổ ngắn', 10000, 300, 5),
    ('STRUCTURING_SUSPICION', 'Nghi vấn chia nhỏ giao dịch', 9000, 3600, 3),
    ('CIRCULAR_TRANSFER', 'Chuỗi chuyển tiền vòng tròn', 5000, 300, 3)
ON CONFLICT (name) DO NOTHING;

CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_event_rule
    ON alerts (event_id, rule_name)
    WHERE event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS ix_alerts_assignee ON alerts (assignee_id);
CREATE INDEX IF NOT EXISTS ix_alerts_account ON alerts (account_id);

CREATE TABLE IF NOT EXISTS alert_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES alerts(alert_id),
    actor_user_id INT REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_files (
    evidence_id BIGSERIAL PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES alerts(alert_id),
    object_key VARCHAR(500) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    size_bytes BIGINT,
    checksum_sha256 VARCHAR(64),
    uploaded_by INT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
