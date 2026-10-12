-- Preserve graph/source evidence carried by benchmark and AML alert envelopes.

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source_event_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS graph_evidence JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS ix_alerts_source_event_ids
    ON alerts USING GIN (source_event_ids);

COMMENT ON COLUMN alerts.source_event_ids IS
    'Immutable source benchmark event IDs that support the alert decision.';
COMMENT ON COLUMN alerts.graph_evidence IS
    'Detection-time graph or rule evidence; never interpreted as source identity.';
