-- Idempotent migration for databases initialized before payment-events v1.
ALTER TABLE core_banking.payment_event
    ADD COLUMN IF NOT EXISTS event_id VARCHAR(120);
ALTER TABLE core_banking.payment_event
    ADD COLUMN IF NOT EXISTS schema_version INT NOT NULL DEFAULT 1;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'core_banking' AND table_name = 'payment_event'
          AND column_name = 'timestamp' AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE core_banking.payment_event
            ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';
    END IF;
END $$;
UPDATE core_banking.payment_event
SET event_id = 'legacy:' || payment_id
WHERE event_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_payment_event_event_id
    ON core_banking.payment_event (event_id) WHERE event_id IS NOT NULL;
