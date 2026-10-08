-- Additive alert trace context. Rollback: stop writers then drop alerts.trace_id.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS trace_id VARCHAR(50);
CREATE INDEX IF NOT EXISTS ix_alerts_trace_id ON alerts (trace_id);
