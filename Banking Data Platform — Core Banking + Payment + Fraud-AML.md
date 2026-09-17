# 🏦 Banking Data Platform
## Core Banking + Payment + Fraud / AML

> End-to-end Data Engineering project mô phỏng một nền tảng dữ liệu ngân hàng, bao gồm **Core Banking**, **Payment Processing**, **Real-time Fraud Detection** và **AML Transaction Monitoring**.

---

## 1. 📌 Project Overview

Project xây dựng một **Banking Data Platform** có khả năng:

- Thu thập dữ liệu từ nhiều hệ thống ngân hàng.
- Xử lý dữ liệu batch và streaming.
- Xây dựng Data Lake.
- Xây dựng Banking Data Warehouse.
- Xử lý giao dịch thanh toán theo thời gian thực.
- Phát hiện các giao dịch có dấu hiệu gian lận.
- Phát hiện các pattern giao dịch đáng ngờ phục vụ AML.
- Xây dựng Data Quality và Data Governance.
- Cung cấp dữ liệu cho BI, Risk và Compliance.
- Monitoring toàn bộ data pipeline.

### Mục tiêu chính

```text
                    Banking Data Platform
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   Core Banking         Payment System       Fraud / AML
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                     Data Platform
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
           Data Lake    Data Warehouse   Streaming
               │            │            │
               └────────────┼────────────┘
                            ▼
                   Analytics / Dashboard
```

---

# 2. 🎯 Project Goals

Project tập trung vào các năng lực Data Engineering sau:

### Data Engineering

- Data ingestion
- ETL / ELT
- Batch processing
- Stream processing
- CDC
- Data modeling
- Data Lake
- Data Warehouse
- Data Quality
- Data validation
- Data lineage
- Data partitioning
- Incremental processing

### Distributed Systems

- Apache Kafka
- Apache Spark
- Event-driven architecture
- Distributed processing

### Banking Domain

- Customer
- Account
- Transaction
- Payment
- Card
- Loan
- Merchant
- Branch
- Fraud
- AML

### Production Engineering

- Docker
- Monitoring
- Logging
- Alerting
- CI/CD
- Testing

---

# 3. 🏗️ High-Level Architecture

```text
                           ┌──────────────────┐
                           │   Customer App   │
                           └────────┬─────────┘
                                    │
                           ┌────────▼─────────┐
                           │  Banking Systems │
                           └────────┬─────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
       Core Banking            Payment System          CRM / Loan
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                           CDC / API / Batch
                                    │
                                    ▼
                             Apache Kafka
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              Raw Events       Payment Events   Customer Events
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                         Spark Structured Streaming
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
             Fraud Engine       AML Engine       Aggregation
                  │                 │                 │
                  └─────────────────┼─────────────────┘
                                    │
                                    ▼
                              Data Lake
                             MinIO / S3
                                    │
                                    ▼
                              Apache Spark
                                    │
                                    ▼
                           Data Warehouse
                         PostgreSQL / ClickHouse
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 Grafana        Metabase           API
```

---

# 4. 🧩 Project Domains

Project gồm 3 domain chính:

```text
Core Banking
     │
     ├── Customer
     ├── Account
     ├── Branch
     ├── Loan
     └── Balance
     
Payment
     │
     ├── Card Payment
     ├── Transfer
     ├── ATM
     ├── POS
     └── Online Payment

Fraud / AML
     │
     ├── Fraud Detection
     ├── Transaction Monitoring
     ├── Risk Scoring
     ├── Suspicious Activity
     └── Alert Management
```

---

# 5. 🏦 Core Banking Domain

## 5.1 Customer

Thông tin khách hàng:

```text
customer_id
first_name
last_name
date_of_birth
gender
email
phone
address
country
customer_type
created_at
updated_at
```

Không sử dụng dữ liệu cá nhân thật.

Có thể sử dụng:

- Synthetic data
- Faker
- Data generator

---

# 5.2 Account

```text
account_id
customer_id
account_type
currency
balance
status
opened_at
closed_at
branch_id
created_at
updated_at
```

Account types:

```text
SAVINGS
CHECKING
CURRENT
FIXED_DEPOSIT
```

---

# 5.3 Branch

```text
branch_id
branch_name
city
country
latitude
longitude
created_at
```

Có thể sử dụng dữ liệu địa lý giả lập.

---

# 5.4 Loan

```text
loan_id
customer_id
loan_product_id
principal_amount
interest_rate
term_months
start_date
maturity_date
status
created_at
```

Loan status:

```text
PENDING
APPROVED
ACTIVE
PAID
DEFAULT
CLOSED
```

---

# 5.5 Account Transaction

```text
transaction_id
account_id
customer_id
transaction_type
amount
currency
balance_before
balance_after
timestamp
channel
status
reference_id
```

Transaction types:

```text
DEPOSIT
WITHDRAWAL
TRANSFER
PAYMENT
REFUND
FEE
INTEREST
```

---

# 6. 💳 Payment Domain

Payment system xử lý các loại:

```text
Card Payment
Bank Transfer
ATM
POS
QR Payment
Online Payment
```

## Payment Event

```json
{
  "payment_id": "PAY_001",
  "customer_id": "CUS_1001",
  "account_id": "ACC_1001",
  "merchant_id": "MER_100",
  "amount": 250.50,
  "currency": "USD",
  "payment_method": "CARD",
  "channel": "POS",
  "location": "Hanoi",
  "device_id": "DEV_001",
  "timestamp": "2026-09-01T10:30:00",
  "status": "SUCCESS"
}
```

---

# 7. 🔄 Payment Lifecycle

Một payment có thể trải qua:

```text
CREATED
   ↓
AUTHORIZED
   ↓
PROCESSING
   ↓
COMPLETED
```

Nếu thất bại:

```text
AUTHORIZED
    ↓
FAILED
```

Hoặc:

```text
COMPLETED
    ↓
REFUNDED
```

---

# 8. ⚡ Real-time Payment Pipeline

```text
Payment Application
        │
        ▼
   Payment API
        │
        ▼
      Kafka
        │
        ▼
Spark Structured Streaming
        │
        ├───────────────┐
        │               │
        ▼               ▼
 Fraud Detection    Payment Processing
        │               │
        ▼               ▼
   Fraud Result     Payment Result
        │               │
        └───────┬───────┘
                ▼
          PostgreSQL
                │
                ▼
             Grafana
```

---

# 9. 🦠 Fraud Detection

Fraud detection tập trung vào việc phát hiện các giao dịch có pattern bất thường.

## 9.1 Fraud Rules

### Rule 1 — Transaction Velocity

Một customer thực hiện quá nhiều transaction trong thời gian ngắn.

```text
10 transactions
within 1 minute
```

→ suspicious.

---

### Rule 2 — Large Transaction

```text
amount > threshold
```

Ví dụ:

```text
amount > 10,000 USD
```

---

### Rule 3 — Location Anomaly

Customer thực hiện:

```text
Vietnam
   ↓
5 minutes
   ↓
USA
```

→ suspicious travel pattern.

---

### Rule 4 — Multiple Devices

Một account sử dụng nhiều device trong thời gian ngắn.

```text
Account A
 ├── Device 01
 ├── Device 02
 ├── Device 03
 └── Device 04
```

---

### Rule 5 — Unusual Amount

So sánh transaction hiện tại với historical behavior.

```text
Customer average = $100

Current transaction = $5,000
```

→ suspicious.

---

# 10. 🧮 Fraud Score

Có thể xây một scoring system:

```text
fraud_score =
    velocity_score
  + amount_score
  + location_score
  + device_score
  + behavioral_score
```

Ví dụ:

```text
0 - 30    → LOW
31 - 60   → MEDIUM
61 - 80   → HIGH
81 - 100  → CRITICAL
```

Đây là **mô hình kỹ thuật của project**, không phải tiêu chuẩn ngân hàng thực tế.

---

# 11. 🚨 Fraud Decision

```text
Fraud Score
     │
     ├── LOW
     │     ↓
     │   Approve
     │
     ├── MEDIUM
     │     ↓
     │   Monitor
     │
     ├── HIGH
     │     ↓
     │   Review
     │
     └── CRITICAL
           ↓
        Block / Alert
```

---

# 12. 🕵️ AML Transaction Monitoring

AML module tập trung vào **transaction patterns** thay vì chỉ kiểm tra một transaction riêng lẻ.

## Ví dụ Pattern 1 — Structuring

Nhiều giao dịch nhỏ được thực hiện liên tiếp.

```text
$9,000
$9,200
$9,500
$8,900
$9,100
```

Hệ thống đánh dấu pattern để review.

---

# 13. AML Pattern 2 — Rapid Movement

```text
Account A
    ↓
Account B
    ↓
Account C
    ↓
Account D
```

Tiền di chuyển qua nhiều account trong thời gian ngắn.

---

# 14. AML Pattern 3 — Circular Transactions

```text
A → B
B → C
C → D
D → A
```

Có thể sử dụng graph analytics để phát hiện.

---

# 15. AML Pattern 4 — High-Risk Activity

Kết hợp:

```text
customer
account
transaction
country
merchant
device
```

để tạo monitoring rules.

---

# 16. 🔗 Transaction Graph

Xây dựng graph:

```text
Customer
   │
   ▼
 Account
   │
   ▼
Transaction
   │
   ├──────► Account
   │
   └──────► Merchant
```

Ví dụ:

```text
CUS_01
  │
  ▼
ACC_01
  │
  ├──→ ACC_02
  │      │
  │      └──→ ACC_03
  │
  └──→ ACC_04
```

Có thể sử dụng:

```text
Neo4j
NetworkX
Apache Spark GraphFrames
```

để nghiên cứu graph analytics.

---

# 17. 📡 Kafka Architecture

Kafka được sử dụng làm event backbone.

## Topics

```text
customer-events
account-events
transaction-events
payment-events
fraud-events
aml-events
alert-events
```

Ví dụ:

```text
payment-events
       │
       ├── Spark Streaming
       ├── Fraud Engine
       └── Data Lake
```

---

# 18. ⚡ Spark Structured Streaming

Spark Streaming xử lý:

```text
Kafka
  ↓
Parse JSON
  ↓
Schema Validation
  ↓
Data Cleaning
  ↓
Window Aggregation
  ↓
Fraud Rules
  ↓
AML Rules
  ↓
Sink
```

Ví dụ window:

```text
5-minute window
```

để tính:

```text
transaction_count
total_amount
unique_devices
unique_locations
```

---

# 19. 🗄️ Data Lake

Sử dụng:

```text
MinIO
```

để mô phỏng:

```text
Amazon S3
```

Data Lake structure:

```text
data-lake/
│
├── raw/
│   ├── customer/
│   ├── account/
│   ├── transaction/
│   └── payment/
│
├── bronze/
│
├── silver/
│
└── gold/
```

---

# 20. 🥉 Bronze Layer

Raw data sau ingestion.

```text
Kafka
 ↓
Bronze
```

Không thay đổi nhiều dữ liệu gốc.

---

# 21. 🥈 Silver Layer

Cleaned data:

```text
Bronze
   ↓
Spark
   ↓
Silver
```

Xử lý:

- schema validation
- null handling
- duplicate removal
- type conversion
- standardization
- invalid records

---

# 22. 🥇 Gold Layer

Business-ready data:

```text
Silver
   ↓
Spark
   ↓
Gold
```

Ví dụ:

```text
daily_transaction_summary
customer_transaction_summary
payment_summary
fraud_summary
aml_alert_summary
```

---

# 23. 🏛️ Data Warehouse

Data Warehouse sử dụng:

```text
PostgreSQL
```

hoặc:

```text
ClickHouse
```

## Dimensions

```text
dim_customer
dim_account
dim_branch
dim_merchant
dim_payment_method
dim_channel
dim_date
dim_device
```

## Facts

```text
fact_transaction
fact_payment
fact_loan
fact_fraud
fact_aml_alert
fact_account_balance
```

---

# 24. ⭐ Star Schema

```text
                 dim_customer
                      │
                      │
dim_account ─── fact_transaction ─── dim_date
                      │
                      │
                dim_channel
                      │
                      │
                dim_merchant
```

---

# 25. 🔄 CDC

Nếu muốn nâng cấp project, triển khai Change Data Capture.

Architecture:

```text
PostgreSQL
    ↓
Debezium
    ↓
Kafka
    ↓
Spark
    ↓
Data Lake / DWH
```

CDC events:

```text
INSERT
UPDATE
DELETE
```

Ví dụ:

```text
Customer balance changed
        ↓
CDC event
        ↓
Kafka
        ↓
Streaming pipeline
```

---

# 26. ⏰ Batch Processing

Airflow dùng để orchestrate batch jobs.

```text
Airflow
   │
   ├── Extract
   ├── Validate
   ├── Transform
   ├── Load
   ├── Data Quality
   └── Reporting
```

Ví dụ DAG:

```text
start
  ↓
extract_customer
  ↓
extract_account
  ↓
extract_transaction
  ↓
validate_data
  ↓
transform
  ↓
load_dwh
  ↓
run_quality_checks
  ↓
generate_report
```

---

# 27. 🧪 Data Quality

Các validation rules:

### Completeness

```text
customer_id IS NOT NULL
account_id IS NOT NULL
transaction_id IS NOT NULL
```

### Uniqueness

```text
transaction_id UNIQUE
payment_id UNIQUE
customer_id UNIQUE
```

### Valid Amount

```text
amount > 0
```

### Referential Integrity

```text
transaction.account_id
        ↓
dim_account.account_id
```

### Freshness

```text
latest_event_timestamp
```

### Volume

Kiểm tra bất thường về số lượng records.

```text
Yesterday: 1,000,000

Today: 10,000

→ ALERT
```

---

# 28. 🔐 Data Security

Project phải mô phỏng các nguyên tắc bảo vệ dữ liệu ngân hàng.

## Encryption

```text
Data in Transit
    ↓
TLS

Data at Rest
    ↓
Encryption
```

## Sensitive Data

Không sử dụng:

- real customer data
- real card number
- real account number
- real identity documents

Có thể masking:

```text
1234567890123456
        ↓
************3456
```

---

# 29. 👥 Access Control

Thiết kế RBAC:

```text
Admin
  ↓
Full Access

Data Engineer
  ↓
Pipeline + Data Platform

Analyst
  ↓
Aggregated Data

Compliance
  ↓
AML / Fraud Data

Viewer
  ↓
Dashboard Only
```

---

# 30. 📊 Monitoring

Sử dụng:

```text
Prometheus
Grafana
```

Theo dõi:

```text
Kafka throughput
Kafka lag
Spark processing time
Pipeline failures
Data freshness
Record count
Fraud alerts
AML alerts
Payment success rate
```

---

# 31. 📈 Dashboard

## Banking Overview

```text
Total Customers
Total Accounts
Total Transactions
Transaction Volume
Total Payment Value
```

## Payment Dashboard

```text
Transactions / minute
Success Rate
Failure Rate
Average Payment
Payment by Channel
Payment by Country
```

## Fraud Dashboard

```text
Fraud Transactions
Fraud Amount
Fraud Score Distribution
Fraud by Channel
Fraud by Location
Alerts by Severity
```

## AML Dashboard

```text
AML Alerts
Suspicious Accounts
Suspicious Transactions
Alert Status
Transaction Networks
```

---

# 32. 🧱 Technology Stack

## Core

```text
Python
SQL
PostgreSQL
```

## Streaming

```text
Apache Kafka
Apache Spark Structured Streaming
```

## Batch

```text
Apache Spark
Apache Airflow
```

## Storage

```text
MinIO
PostgreSQL
ClickHouse
```

## CDC

```text
Debezium
```

## Graph

```text
Neo4j
NetworkX
```

## Monitoring

```text
Prometheus
Grafana
```

## Infrastructure

```text
Docker
Docker Compose
Linux
Git
GitHub
```

---

# 33. 📁 Recommended Repository Structure

```text
banking-data-platform/
│
├── README.md
│
├── docker/
│   ├── docker-compose.yml
│   ├── kafka/
│   ├── spark/
│   ├── postgres/
│   └── grafana/
│
├── ingestion/
│   ├── customer_generator.py
│   ├── account_generator.py
│   ├── transaction_generator.py
│   └── payment_generator.py
│
├── kafka/
│   ├── producers/
│   └── consumers/
│
├── streaming/
│   ├── payment_stream.py
│   ├── fraud_detection.py
│   ├── aml_monitoring.py
│   └── aggregations.py
│
├── batch/
│   ├── customer_pipeline.py
│   ├── transaction_pipeline.py
│   └── warehouse_pipeline.py
│
├── airflow/
│   └── dags/
│       ├── banking_pipeline.py
│       ├── dwh_pipeline.py
│       └── data_quality.py
│
├── warehouse/
│   ├── ddl/
│   ├── dimensions/
│   └── facts/
│
├── fraud/
│   ├── rules/
│   ├── scoring/
│   └── alerts/
│
├── aml/
│   ├── rules/
│   ├── graph/
│   └── alerts/
│
├── data_quality/
│   ├── checks/
│   └── reports/
│
├── monitoring/
│   ├── prometheus/
│   └── grafana/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── data_quality/
│
├── scripts/
│   ├── setup.sh
│   └── generate_data.sh
│
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   ├── security.md
│   └── pipeline.md
│
├── .env.example
├── .gitignore
├── Makefile
└── requirements.txt
```

---

# 34. 📊 Data Generation Strategy

Project không sử dụng dữ liệu ngân hàng thật.

Sử dụng **synthetic data**.

## Customer Generator

Generate:

```text
100,000 customers
```

## Account Generator

Generate:

```text
200,000 accounts
```

## Transaction Generator

Generate:

```text
1M+
transactions
```

## Payment Generator

Generate realtime events:

```text
10 - 100 events/sec
```

Tùy khả năng của máy.

---

# 35. 🔥 Real-time Simulator

Python simulator:

```text
Customer
   ↓
Account
   ↓
Transaction
   ↓
Payment
```

Sinh event:

```json
{
  "event_type": "PAYMENT_CREATED",
  "payment_id": "PAY_100001",
  "customer_id": "CUS_123",
  "account_id": "ACC_123",
  "amount": 450.50,
  "currency": "USD",
  "merchant_id": "MER_100",
  "device_id": "DEV_22",
  "country": "VN",
  "timestamp": "2026-09-17T10:00:00"
}
```

Sau đó publish vào:

```text
Kafka topic:
payment-events
```

---

# 36. 🔀 End-to-End Streaming Flow

```text
Python Simulator
       ↓
     Kafka
       ↓
payment-events
       ↓
Spark Structured Streaming
       ↓
Schema Validation
       ↓
Feature Extraction
       ↓
 ┌─────┴─────┐
 ↓           ↓
Fraud       AML
Engine      Engine
 ↓           ↓
 └─────┬─────┘
       ↓
 Risk / Alert
       ↓
 ┌─────┼───────────┐
 ↓     ↓           ↓
Redis PostgreSQL   MinIO
       ↓
    Grafana
```

---

# 37. 🧠 Advanced Features

Sau khi hoàn thành MVP, có thể nâng cấp:

## Phase 1

```text
PostgreSQL
Python
Airflow
Spark
```

## Phase 2

```text
Kafka
Spark Streaming
MinIO
```

## Phase 3

```text
Fraud Engine
AML Engine
Redis
```

## Phase 4

```text
Debezium
CDC
```

## Phase 5

```text
Neo4j
Graph Analytics
```

## Phase 6

```text
Prometheus
Grafana
Data Quality
```

## Phase 7

```text
CI/CD
Testing
Documentation
Security
```

---

# 38. 🧪 Testing Strategy

## Unit Testing

Test:

```text
fraud rules
AML rules
transformations
validators
scoring
```

## Integration Testing

Test:

```text
Kafka → Spark
Spark → PostgreSQL
Spark → MinIO
Airflow → Spark
```

## Data Quality Testing

Test:

```text
null
duplicate
schema
referential integrity
freshness
volume
```

---

# 39. 🚀 Deployment

Toàn bộ hệ thống có thể chạy local bằng:

```text
Docker Compose
```

Infrastructure:

```text
┌──────────────────────────────────────┐
│             Docker Host              │
│                                      │
│  Kafka                               │
│  Zookeeper / KRaft                   │
│  Spark                               │
│  PostgreSQL                          │
│  MinIO                               │
│  Airflow                             │
│  Redis                               │
│  Grafana                             │
│  Prometheus                          │
│  Neo4j                               │
│                                      │
└──────────────────────────────────────┘
```

---

# 40. 🔄 CI/CD

GitHub Actions:

```text
git push
   ↓
Run Tests
   ↓
Lint
   ↓
Build Docker Images
   ↓
Integration Tests
   ↓
Deploy
```

Có thể sử dụng:

```text
GitHub Actions
Docker
Docker Compose
```

---

# 41. 📌 Development Roadmap

## Phase 1 — Banking Data Model

- [ ] Design customer model
- [ ] Design account model
- [ ] Design transaction model
- [ ] Design payment model
- [ ] Design loan model
- [ ] Design warehouse schema

---

## Phase 2 — Synthetic Data

- [ ] Customer generator
- [ ] Account generator
- [ ] Transaction generator
- [ ] Payment generator
- [ ] Merchant generator
- [ ] Branch generator

---

## Phase 3 — Batch Pipeline

```text
Source
 ↓
Airflow
 ↓
Spark
 ↓
MinIO
 ↓
PostgreSQL
```

Tasks:

- [ ] ingestion
- [ ] cleaning
- [ ] transformation
- [ ] loading
- [ ] incremental processing

---

## Phase 4 — Kafka

- [ ] Kafka setup
- [ ] Create topics
- [ ] Producer
- [ ] Consumer
- [ ] Schema validation
- [ ] Error handling

Topics:

```text
customer-events
account-events
transaction-events
payment-events
```

---

## Phase 5 — Streaming

- [ ] Spark Structured Streaming
- [ ] Kafka integration
- [ ] Window aggregation
- [ ] Stateful processing
- [ ] Sink to PostgreSQL
- [ ] Sink to MinIO

---

## Phase 6 — Fraud

- [ ] Velocity rule
- [ ] Amount rule
- [ ] Location rule
- [ ] Device rule
- [ ] Behavioral rule
- [ ] Fraud scoring
- [ ] Fraud alerts

---

## Phase 7 — AML

- [ ] Transaction monitoring
- [ ] Structuring detection
- [ ] Rapid movement detection
- [ ] Circular transaction detection
- [ ] Suspicious account detection
- [ ] Alert generation

---

## Phase 8 — Graph Analytics

- [ ] Build transaction graph
- [ ] Account relationship
- [ ] Customer relationship
- [ ] Transaction path
- [ ] Circular transaction detection

---

## Phase 9 — Data Quality

- [ ] Null checks
- [ ] Duplicate checks
- [ ] Schema checks
- [ ] Volume checks
- [ ] Freshness checks
- [ ] Referential integrity

---

## Phase 10 — Monitoring

- [ ] Prometheus
- [ ] Grafana
- [ ] Kafka metrics
- [ ] Spark metrics
- [ ] Pipeline metrics
- [ ] Alerting

---

## Phase 11 — Productionization

- [ ] Docker Compose
- [ ] Environment variables
- [ ] Logging
- [ ] Error handling
- [ ] Retry
- [ ] Dead Letter Queue
- [ ] CI/CD
- [ ] Documentation

---

# 42. 📈 Expected Final Architecture

```text
                           USERS
                             │
                             ▼
                      Banking Systems
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
      Core Banking       Payment System       CRM
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                       CDC / API / Batch
                             │
                             ▼
                          KAFKA
                             │
               ┌─────────────┼─────────────┐
               │             │             │
               ▼             ▼             ▼
          Transactions     Payments      Accounts
               │             │             │
               └─────────────┼─────────────┘
                             ▼
                  SPARK STRUCTURED STREAMING
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
           FRAUD            AML          Analytics
           ENGINE          ENGINE          │
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                          MINIO
                             │
                       Spark Batch
                             │
                             ▼
                    DATA WAREHOUSE
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
      BI Dashboard      Risk Analytics     Compliance
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                       Monitoring
                    Prometheus + Grafana
```

---

# 43. 🎓 Data Engineering Concepts Demonstrated

Project hoàn thành sẽ demonstrate:

```text
✓ Python
✓ SQL
✓ PostgreSQL
✓ Data Modeling
✓ Star Schema
✓ Data Warehouse
✓ Data Lake
✓ ETL / ELT
✓ Batch Processing
✓ Apache Spark
✓ Spark Structured Streaming
✓ Apache Kafka
✓ Airflow
✓ CDC
✓ Debezium
✓ MinIO / S3
✓ Redis
✓ Graph Analytics
✓ Data Quality
✓ Data Governance
✓ Monitoring
✓ Prometheus
✓ Grafana
✓ Docker
✓ CI/CD
✓ Testing
```

---

# 44. 💼 CV Description

Có thể mô tả project trên CV:

> **Banking Data Platform — Core Banking, Payment & Fraud/AML**
>
> Designed and implemented an end-to-end banking data platform integrating core banking, payment, fraud detection, and AML transaction monitoring workloads. Built batch and real-time pipelines using Apache Kafka, Spark Structured Streaming, Airflow, PostgreSQL, and MinIO; implemented dimensional data warehouse models, transaction monitoring rules, fraud scoring, data quality checks, and observability with Prometheus and Grafana.

### Technical Keywords

```text
Python
SQL
Apache Kafka
Apache Spark
Spark Structured Streaming
Apache Airflow
PostgreSQL
MinIO
Debezium
Redis
Neo4j
Prometheus
Grafana
Docker
GitHub Actions
```

---

# 45. 🏁 Definition of Done

Project được xem là hoàn thành khi:

- [ ] Có synthetic banking data.
- [ ] Có Core Banking data model.
- [ ] Có Payment data model.
- [ ] Có Data Lake.
- [ ] Có Data Warehouse.
- [ ] Có batch pipeline.
- [ ] Có Kafka streaming pipeline.
- [ ] Có Spark Structured Streaming.
- [ ] Có Fraud Detection.
- [ ] Có AML Monitoring.
- [ ] Có transaction graph.
- [ ] Có Data Quality.
- [ ] Có monitoring.
- [ ] Có Grafana dashboard.
- [ ] Có Docker Compose.
- [ ] Có automated tests.
- [ ] Có CI/CD.
- [ ] Có architecture documentation.
- [ ] Có README hướng dẫn deployment.

---

# 46. ⭐ Portfolio Strategy

Không nên cố gắng xây toàn bộ hệ thống ngay từ đầu.

Nên triển khai theo thứ tự:

```text
                 MVP
                  │
                  ▼
          Core Banking
                  │
                  ▼
              Payment
                  │
                  ▼
              Kafka
                  │
                  ▼
        Spark Streaming
                  │
          ┌───────┴───────┐
          ▼               ▼
        Fraud             AML
          │               │
          └───────┬───────┘
                  ▼
             Data Lake
                  │
                  ▼
          Data Warehouse
                  │
          ┌───────┴────────┐
          ▼                ▼
      Dashboard        Monitoring
```

Sau khi MVP chạy ổn định mới bổ sung:

```text
CDC
Graph Analytics
Redis
Data Quality
Security
CI/CD
```

Mục tiêu cuối cùng không phải chỉ là tạo một hệ thống "banking simulator", mà là xây dựng một **production-style Data Platform** có khả năng ingest, process, store, monitor và serve cả **batch data lẫn real-time banking events**.