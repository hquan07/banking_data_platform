-- Schema for Core Banking Data
CREATE SCHEMA IF NOT EXISTS core_banking;

-- 1. Branch Table
CREATE TABLE IF NOT EXISTS core_banking.branch (
    branch_id VARCHAR(50) PRIMARY KEY,
    branch_name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Customer Table
CREATE TABLE IF NOT EXISTS core_banking.customer (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    email VARCHAR(100),
    phone VARCHAR(50),
    address TEXT,
    country VARCHAR(100),
    customer_type VARCHAR(50), -- RETAIL, CORPORATE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Account Table
CREATE TABLE IF NOT EXISTS core_banking.account (
    account_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES core_banking.customer(customer_id),
    branch_id VARCHAR(50) REFERENCES core_banking.branch(branch_id),
    account_type VARCHAR(50), -- SAVINGS, CHECKING, CURRENT, FIXED_DEPOSIT
    currency VARCHAR(10),
    balance DECIMAL(15, 2) DEFAULT 0.00,
    status VARCHAR(20), -- ACTIVE, INACTIVE, CLOSED, BLOCKED
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Loan Table
CREATE TABLE IF NOT EXISTS core_banking.loan (
    loan_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES core_banking.customer(customer_id),
    loan_product_id VARCHAR(50),
    principal_amount DECIMAL(15, 2),
    interest_rate DECIMAL(5, 2),
    term_months INT,
    start_date DATE,
    maturity_date DATE,
    status VARCHAR(20), -- PENDING, APPROVED, ACTIVE, PAID, DEFAULT, CLOSED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Account Transaction Table
CREATE TABLE IF NOT EXISTS core_banking.transaction (
    transaction_id VARCHAR(50) PRIMARY KEY,
    account_id VARCHAR(50) REFERENCES core_banking.account(account_id),
    customer_id VARCHAR(50) REFERENCES core_banking.customer(customer_id),
    transaction_type VARCHAR(50), -- DEPOSIT, WITHDRAWAL, TRANSFER, PAYMENT, REFUND, FEE, INTEREST
    amount DECIMAL(15, 2),
    currency VARCHAR(10),
    balance_before DECIMAL(15, 2),
    balance_after DECIMAL(15, 2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel VARCHAR(50), -- BRANCH, ATM, MOBILE, INTERNET, POS
    status VARCHAR(20), -- SUCCESS, FAILED, PENDING
    reference_id VARCHAR(100)
);

-- 6. Raw Payments Table (for initial batch load / simulation target)
CREATE TABLE IF NOT EXISTS core_banking.payment_event (
    payment_id VARCHAR(50) PRIMARY KEY,
    trace_id VARCHAR(50),
    customer_id VARCHAR(50),
    account_id VARCHAR(50),
    merchant_id VARCHAR(50),
    amount DECIMAL(15, 2),
    currency VARCHAR(10),
    payment_method VARCHAR(50), -- CARD, BANK_TRANSFER, QR
    channel VARCHAR(50), -- POS, ONLINE, ATM
    location VARCHAR(100),
    device_id VARCHAR(50),
    timestamp TIMESTAMP,
    status VARCHAR(20)
);

-- ==========================================
-- RBAC (Role-Based Access Control)
-- ==========================================

-- Create privilege groups without credentials. Runtime login roles are
-- provisioned outside schema DDL by the deployment environment.
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'etl_user') THEN
      CREATE ROLE etl_user NOLOGIN;
   END IF;
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'dashboard_user') THEN
      CREATE ROLE dashboard_user NOLOGIN;
   END IF;
END
$do$;

-- Grant privileges for core_banking
GRANT USAGE ON SCHEMA core_banking TO etl_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core_banking TO etl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA core_banking GRANT ALL ON TABLES TO etl_user;

GRANT USAGE ON SCHEMA core_banking TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA core_banking TO dashboard_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA core_banking GRANT SELECT ON TABLES TO dashboard_user;
