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

INSERT INTO benchmark_model_candidates (
    version, dataset_id, algorithm, feature_schema, train_rows, holdout_rows,
    dataset_sha256, model_sha256, metrics, evaluation_scope, decision,
    production_eligible, explanation_status
)
VALUES (
    'ds4-histgb-v1',
    'ds4_baf',
    'HistGradientBoostingClassifier',
    '["income","name_email_similarity","prev_address_months_count","current_address_months_count","customer_age","days_since_request","intended_balcon_amount","payment_type","zip_count_4w","velocity_6h","velocity_24h","velocity_4w","bank_branch_count_8w","date_of_birth_distinct_emails_4w","employment_status","credit_risk_score","email_is_free","housing_status","phone_home_valid","phone_mobile_valid","bank_months_count","has_other_cards","proposed_credit_limit","foreign_request","source","session_length_in_minutes","device_os","keep_alive_session","device_distinct_emails_8w","device_fraud_count"]'::jsonb,
    794989,
    96843,
    '7bf10a37ce07e72e14c1b09e5efee3d27261baff4facc7da767b0474dcf9b809',
    '7ab242cf97351b71e28e6dabafdd128fab626a88412ece2afa4587bc8bc8e2b7',
    '{"precision":0.28426051560379917,"recall":0.2934173669467787,"f1":0.28876636802205374,"pr_auc":0.21244953529616378,"roc_auc":0.8963353878993299,"false_positive_rate":0.011056961693654038,"true_positive":419,"false_positive":1055,"false_negative":1009,"true_negative":94360,"validation_rows":108168,"decision_threshold":0.9059238524732356}'::jsonb,
    'ds4_month_0_5_train_6_validation_7_holdout',
    'CANDIDATE_NOT_DEPLOYED',
    FALSE,
    'No SHAP or causal explanations are emitted by this candidate pipeline'
)
ON CONFLICT (version) DO NOTHING;
