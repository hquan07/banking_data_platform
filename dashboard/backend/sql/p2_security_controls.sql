-- Durable sessions, append-only security events and explicit audit retention.
-- Additive and idempotent. Session rows may be purged after expiry; security
-- events cannot be updated and cannot be deleted before retain_until.

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_jti UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoke_reason VARCHAR(80),
    source_fingerprint VARCHAR(64) NOT NULL,
    user_agent_fingerprint VARCHAR(64) NOT NULL,
    CHECK (expires_at > issued_at),
    CHECK (revoked_at IS NULL OR revoke_reason IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_active
    ON auth_sessions (user_id, expires_at DESC)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS security_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    outcome VARCHAR(30) NOT NULL,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_jti UUID,
    source_fingerprint VARCHAR(64) NOT NULL,
    subject_fingerprint VARCHAR(64),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retain_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '365 days')
);

CREATE INDEX IF NOT EXISTS ix_security_events_occurred
    ON security_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_security_events_type_outcome
    ON security_events (event_type, outcome, occurred_at DESC);

CREATE OR REPLACE FUNCTION enforce_security_event_retention()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'security_events are append-only';
    END IF;
    IF OLD.retain_until > NOW() THEN
        RAISE EXCEPTION 'security event % is retained until %',
            OLD.event_id, OLD.retain_until;
    END IF;
    RETURN OLD;
END
$$;

DROP TRIGGER IF EXISTS trg_security_events_retention ON security_events;
CREATE TRIGGER trg_security_events_retention
BEFORE UPDATE OR DELETE ON security_events
FOR EACH ROW EXECUTE FUNCTION enforce_security_event_retention();

COMMENT ON TABLE auth_sessions IS
    'Server-side JWT session state supporting immediate revocation.';
COMMENT ON TABLE security_events IS
    'Append-only authentication, authorization and rate-limit evidence.';

