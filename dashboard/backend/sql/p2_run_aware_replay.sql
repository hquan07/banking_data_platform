-- Isolate benchmark materializations and alerts by durable replay run.
ALTER TABLE benchmark_events ADD COLUMN IF NOT EXISTS run_id UUID;
ALTER TABLE benchmark_evaluations ADD COLUMN IF NOT EXISTS run_id UUID;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES pipeline_runs(run_id) ON DELETE SET NULL;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_requested_rate_check;
ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_requested_rate_check CHECK (requested_rate >= 0);

DO $$
DECLARE
    dataset RECORD;
    legacy_run UUID;
    owner_id INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM benchmark_events WHERE run_id IS NULL) THEN
        SELECT id INTO owner_id FROM users ORDER BY (role = 'ADMIN') DESC, id LIMIT 1;
        IF owner_id IS NULL THEN
            RAISE EXCEPTION 'Cannot migrate benchmark events without an owner user';
        END IF;
        FOR dataset IN SELECT DISTINCT dataset_id FROM benchmark_events WHERE run_id IS NULL LOOP
            legacy_run := (
                substr(md5('legacy-benchmark-run:' || dataset.dataset_id), 1, 8) || '-' ||
                substr(md5('legacy-benchmark-run:' || dataset.dataset_id), 9, 4) || '-' ||
                substr(md5('legacy-benchmark-run:' || dataset.dataset_id), 13, 4) || '-' ||
                substr(md5('legacy-benchmark-run:' || dataset.dataset_id), 17, 4) || '-' ||
                substr(md5('legacy-benchmark-run:' || dataset.dataset_id), 21, 12)
            )::UUID;
            INSERT INTO pipeline_runs
                (run_id, status, owner_user_id, source_kind, dataset_id,
                 dataset_version, dataset_hash, contract_version,
                 evaluator_version, requested_rate, started_at, completed_at)
            VALUES
                (legacy_run, 'COMPLETED', owner_id, 'MANUAL_REPLAY', dataset.dataset_id,
                 'legacy-pre-p2', repeat('0', 64), 1, 'benchmark-rules-v2', 1,
                 NOW(), NOW())
            ON CONFLICT (run_id) DO NOTHING;
            UPDATE benchmark_events
            SET run_id = legacy_run
            WHERE dataset_id = dataset.dataset_id AND run_id IS NULL;
        END LOOP;
    END IF;
END $$;

UPDATE benchmark_evaluations evaluation
SET run_id = event.run_id
FROM benchmark_events event
WHERE evaluation.run_id IS NULL AND evaluation.event_id = event.event_id;

UPDATE alerts alert
SET run_id = event.run_id
FROM benchmark_events event
WHERE alert.run_id IS NULL
  AND alert.dataset_id = event.dataset_id
  AND alert.event_id = event.event_id;

ALTER TABLE benchmark_events ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE benchmark_evaluations ALTER COLUMN run_id SET NOT NULL;

ALTER TABLE benchmark_evaluations
    DROP CONSTRAINT IF EXISTS benchmark_evaluations_event_id_fkey;
ALTER TABLE benchmark_evaluations
    DROP CONSTRAINT IF EXISTS benchmark_evaluations_run_event_fkey;
ALTER TABLE benchmark_events
    DROP CONSTRAINT IF EXISTS benchmark_events_pkey;
ALTER TABLE benchmark_events
    DROP CONSTRAINT IF EXISTS benchmark_events_dataset_id_source_row_id_key;
ALTER TABLE benchmark_evaluations
    DROP CONSTRAINT IF EXISTS benchmark_evaluations_event_id_evaluator_version_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'benchmark_events_pkey' AND conrelid = 'benchmark_events'::regclass
    ) THEN
        ALTER TABLE benchmark_events
            ADD CONSTRAINT benchmark_events_pkey PRIMARY KEY (run_id, event_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'benchmark_events_run_fkey'
    ) THEN
        ALTER TABLE benchmark_events
            ADD CONSTRAINT benchmark_events_run_fkey
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'benchmark_events_run_source_key'
    ) THEN
        ALTER TABLE benchmark_events
            ADD CONSTRAINT benchmark_events_run_source_key
            UNIQUE (run_id, dataset_id, source_row_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'benchmark_evaluations_run_event_fkey'
    ) THEN
        ALTER TABLE benchmark_evaluations
            ADD CONSTRAINT benchmark_evaluations_run_event_fkey
            FOREIGN KEY (run_id, event_id)
            REFERENCES benchmark_events(run_id, event_id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'benchmark_evaluations_run_event_evaluator_key'
    ) THEN
        ALTER TABLE benchmark_evaluations
            ADD CONSTRAINT benchmark_evaluations_run_event_evaluator_key
            UNIQUE (run_id, event_id, evaluator_version);
    END IF;
END $$;

DROP INDEX IF EXISTS ux_alerts_event_rule;
CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_live_event_rule
    ON alerts (event_id, rule_name)
    WHERE event_id IS NOT NULL AND run_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_run_event_rule
    ON alerts (run_id, event_id, rule_name)
    WHERE event_id IS NOT NULL AND run_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_benchmark_events_run ON benchmark_events (run_id, ingested_at);
CREATE INDEX IF NOT EXISTS ix_benchmark_evaluations_run ON benchmark_evaluations (run_id, evaluated_at);
CREATE INDEX IF NOT EXISTS ix_alerts_run ON alerts (run_id, created_at DESC);
