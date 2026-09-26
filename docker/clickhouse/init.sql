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
