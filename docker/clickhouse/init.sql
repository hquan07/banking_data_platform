CREATE DATABASE IF NOT EXISTS banking_warehouse;

USE banking_warehouse;

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id String,
    first_name String,
    last_name String,
    email String,
    phone String,
    address String,
    city String,
    account_id String,
    account_type String,
    balance Float64,
    account_status String
) ENGINE = MergeTree()
ORDER BY (customer_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS payment_events (
    payment_id String,
    event_id String,
    trace_id String,
    customer_id String,
    account_id String,
    merchant_id String,
    amount Decimal(18, 2),
    currency String,
    payment_method String,
    channel String,
    location String,
    device_id String,
    status String,
    event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY payment_id;
