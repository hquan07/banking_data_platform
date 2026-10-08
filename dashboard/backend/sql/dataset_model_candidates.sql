-- Audited offline model results. Model binaries remain outside the application image.

CREATE TABLE IF NOT EXISTS benchmark_model_candidates (
    version VARCHAR(80) PRIMARY KEY,
    dataset_id VARCHAR(40) NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    feature_schema JSONB NOT NULL,
    train_rows INTEGER NOT NULL CHECK (train_rows > 0),
    holdout_rows INTEGER NOT NULL CHECK (holdout_rows > 0),
    dataset_sha256 CHAR(64) NOT NULL,
    model_sha256 CHAR(64) NOT NULL,
    metrics JSONB NOT NULL,
    evaluation_scope VARCHAR(120) NOT NULL,
    decision VARCHAR(80) NOT NULL,
    production_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    explanation_status TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO benchmark_model_candidates (
    version, dataset_id, algorithm, feature_schema, train_rows, holdout_rows,
    dataset_sha256, model_sha256, metrics, evaluation_scope, decision,
    production_eligible, explanation_status
)
VALUES (
    'ds1-isolation-v1',
    'ds1_creditcard',
    'IsolationForest',
    '["V1","V2","V3","V4","V5","V6","V7","V8","V9","V10","V11","V12","V13","V14","V15","V16","V17","V18","V19","V20","V21","V22","V23","V24","V25","V26","V27","V28"]'::jsonb,
    227845,
    56962,
    '76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89',
    'c26b522b0d64bffb93b803ea539c1e05fd6cc49223be74cc6e82477561bc9d1f',
    '{"precision":0.03278688524590164,"recall":0.02666666666666667,"pr_auc":0.06014320248475371,"false_positive_rate":0.0010371438114156134,"true_positive":2,"false_positive":59,"false_negative":73,"true_negative":56828}'::jsonb,
    'ds1_relative_time_holdout',
    'CANDIDATE_NOT_DEPLOYED',
    FALSE,
    'No per-feature SHAP values are emitted by this Isolation Forest pipeline'
)
ON CONFLICT (version) DO NOTHING;
