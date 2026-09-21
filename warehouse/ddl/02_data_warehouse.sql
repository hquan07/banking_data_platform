-- Schema for Data Warehouse (Star Schema)
CREATE SCHEMA IF NOT EXISTS data_warehouse;

-- ==========================================
-- DIMENSIONS
-- ==========================================

-- 1. Dim Date
CREATE TABLE IF NOT EXISTS data_warehouse.dim_date (
    date_sk INT PRIMARY KEY, -- YYYYMMDD
    full_date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    quarter INT NOT NULL,
    day_of_week INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. Dim Branch
CREATE TABLE IF NOT EXISTS data_warehouse.dim_branch (
    branch_sk SERIAL PRIMARY KEY,
    branch_id VARCHAR(50) NOT NULL,
    branch_name VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100),
    effective_start_date TIMESTAMP,
    effective_end_date TIMESTAMP,
    is_current BOOLEAN
);

-- 3. Dim Customer
CREATE TABLE IF NOT EXISTS data_warehouse.dim_customer (
    customer_sk SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    age_group VARCHAR(20),
    gender VARCHAR(20),
    country VARCHAR(100),
    customer_type VARCHAR(50),
    effective_start_date TIMESTAMP,
    effective_end_date TIMESTAMP,
    is_current BOOLEAN
);

-- 4. Dim Account
CREATE TABLE IF NOT EXISTS data_warehouse.dim_account (
    account_sk SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    customer_sk INT REFERENCES data_warehouse.dim_customer(customer_sk),
    branch_sk INT REFERENCES data_warehouse.dim_branch(branch_sk),
    account_type VARCHAR(50),
    status VARCHAR(20),
    effective_start_date TIMESTAMP,
    effective_end_date TIMESTAMP,
    is_current BOOLEAN
);

-- 5. Dim Merchant
CREATE TABLE IF NOT EXISTS data_warehouse.dim_merchant (
    merchant_sk SERIAL PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL,
    merchant_name VARCHAR(100),
    category VARCHAR(50),
    country VARCHAR(100)
);

-- 6. Dim Device
CREATE TABLE IF NOT EXISTS data_warehouse.dim_device (
    device_sk SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    device_type VARCHAR(50),
    os VARCHAR(50)
);

-- ==========================================
-- FACTS
-- ==========================================

-- 1. Fact Transaction
CREATE TABLE IF NOT EXISTS data_warehouse.fact_transaction (
    transaction_sk SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    date_sk INT REFERENCES data_warehouse.dim_date(date_sk),
    account_sk INT REFERENCES data_warehouse.dim_account(account_sk),
    transaction_type VARCHAR(50),
    channel VARCHAR(50),
    amount DECIMAL(15, 2),
    currency VARCHAR(10),
    status VARCHAR(20),
    timestamp TIMESTAMP
);

-- 2. Fact Payment
CREATE TABLE IF NOT EXISTS data_warehouse.fact_payment (
    payment_sk SERIAL PRIMARY KEY,
    payment_id VARCHAR(50) NOT NULL,
    date_sk INT REFERENCES data_warehouse.dim_date(date_sk),
    account_sk INT REFERENCES data_warehouse.dim_account(account_sk),
    merchant_sk INT REFERENCES data_warehouse.dim_merchant(merchant_sk),
    device_sk INT REFERENCES data_warehouse.dim_device(device_sk),
    amount DECIMAL(15, 2),
    currency VARCHAR(10),
    payment_method VARCHAR(50),
    channel VARCHAR(50),
    location VARCHAR(100),
    status VARCHAR(20),
    timestamp TIMESTAMP
);

-- 3. Fact Fraud Alert
CREATE TABLE IF NOT EXISTS data_warehouse.fact_fraud_alert (
    alert_sk SERIAL PRIMARY KEY,
    payment_sk INT REFERENCES data_warehouse.fact_payment(payment_sk),
    date_sk INT REFERENCES data_warehouse.dim_date(date_sk),
    fraud_score INT,
    risk_level VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
    triggered_rules TEXT,
    decision VARCHAR(50), -- APPROVE, MONITOR, REVIEW, BLOCK
    timestamp TIMESTAMP
);

-- ==========================================
-- RBAC (Role-Based Access Control)
-- ==========================================

-- Grant privileges for data_warehouse
GRANT USAGE ON SCHEMA data_warehouse TO etl_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA data_warehouse TO etl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA data_warehouse GRANT ALL ON TABLES TO etl_user;

GRANT USAGE ON SCHEMA data_warehouse TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA data_warehouse TO dashboard_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA data_warehouse GRANT SELECT ON TABLES TO dashboard_user;
