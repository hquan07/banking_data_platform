-- Additive migration. Rollback: stop clients using version, then drop these indexes
-- and alerts.version; retain alert_audit_log so investigation history is not lost.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS ix_alerts_payment ON alerts (payment_id);
CREATE INDEX IF NOT EXISTS ix_alerts_rule ON alerts (rule_name);
CREATE INDEX IF NOT EXISTS ix_alerts_risk_level ON alerts (risk_level);
CREATE INDEX IF NOT EXISTS ix_alerts_status_created ON alerts (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_alert_audit_alert_created
    ON alert_audit_log (alert_id, created_at DESC);
