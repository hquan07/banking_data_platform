# Kế hoạch hoàn thiện Banking Data Platform

## 1. Mục tiêu và phạm vi

Mục tiêu là đưa dự án từ trạng thái PoC/demo sang hệ thống có thể:

- khởi động nhất quán bằng Docker Compose;
- xử lý giao dịch thật từ producer đến fraud/AML engine;
- lưu alert, lịch sử giao dịch và dữ liệu phân tích đúng schema;
- cung cấp dashboard có authentication/authorization đáng tin cậy;
- có kiểm thử tự động, observability và khả năng vận hành;
- tách bạch rõ chế độ demo/mock với chế độ tích hợp thật.

Phạm vi gồm ingestion/Kafka, Spark Streaming, PostgreSQL, ClickHouse, Redis, Neo4j, MinIO, Airflow, batch, data quality, FastAPI, React, fraud/AML, ML, monitoring và security.

Không xem hệ thống là production-ready cho đến khi hoàn thành tối thiểu toàn bộ P0 và các tiêu chí data integrity/security tương ứng.

## 2. Nguyên tắc triển khai

1. Schema và data contract phải được chốt trước khi sửa producer/consumer.
2. Mock mode phải được bật rõ ràng bằng biến môi trường, không fallback âm thầm.
3. Dependency quan trọng phải có health check, logs và metrics.
4. Production mode phải fail closed khi thiếu secret hoặc datastore bắt buộc.
5. Event và alert phải idempotent; retry không được tạo duplicate.
6. Mọi schema change phải có migration và rollback strategy.
7. Không commit generated artifacts như node_modules, .vite, dist hoặc model artifact không có metadata.

---

# P0 — Khắc phục blocker để chạy end-to-end

## P0.1. Chuẩn hóa configuration và secrets

### Công việc

- Chuẩn hóa các biến:
  - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD;
  - KAFKA_BOOTSTRAP_SERVERS;
  - REDIS_HOST, REDIS_PORT;
  - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD;
  - CLICKHOUSE_HOST, CLICKHOUSE_HTTP_PORT, CLICKHOUSE_NATIVE_PORT;
  - MINIO_ENDPOINT, MINIO_PUBLIC_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD;
  - JWT_SECRET_KEY;
  - APP_MODE=demo|integration|production;
  - ENABLE_MOCK_DATA=false.
- Truyền cấu hình đầy đủ vào backend, Spark, Airflow và worker trong docker-compose.yml.
- Tách endpoint nội bộ container khỏi endpoint public cho browser.
- Thêm startup validation; production mode phải dừng nếu thiếu secret/database credentials.
- Bỏ password placeholder trong DDL; dùng migration/bootstrap theo environment.
- Pin version các image đang dùng latest.

### Tiêu chí nghiệm thu

- docker compose config không còn biến quan trọng bị rỗng.
- Backend kết nối được PostgreSQL, Redis, Neo4j, ClickHouse và MinIO.
- Không còn localhost trong code chạy bên trong container.
- Secret không xuất hiện trong source code hoặc log.

## P0.2. Hoàn thiện PostgreSQL schema và migration

### Công việc

- Tạo migration versioned cho users, alerts, rules, audit logs và evidence metadata.
- Schema alerts tối thiểu gồm alert_id, event_id/payment_id unique, account_id, rule_name, amount, risk_score, risk_level, status, xai_explanation, assignee_id, notes, evidence_file_url, created_at, updated_at, resolved_at.
- Đảm bảo migration users chạy trước các foreign key tới users.
- Thêm index cho created_at, status, assignee_id và account_id.
- Thêm constraint cho status, risk_level và risk_score.
- Dùng migration workflow có thứ tự rõ ràng, không phụ thuộc vào mount SQL ngẫu nhiên.
- Hỗ trợ migration an toàn cho database đã tồn tại.

### Tiêu chí nghiệm thu

- Database mới từ volume rỗng chạy được login, alerts và rules.
- Không còn lỗi relation does not exist.
- Chạy migration lần hai không tạo duplicate hoặc phá schema.
- CI có bước kiểm tra schema.

## P0.3. Sửa backend startup và lifecycle

### Công việc

- Dùng connection pool thay vì global pg_conn dùng chung.
- Thêm startup health check cho dependencies.
- Chỉ chạy Kafka consumer/simulator theo APP_MODE.
- Không chạy simulate_events trong integration/production.
- Lưu task handle và cancel/await khi shutdown.
- Thêm /api/health/live và /api/health/ready.
- Readiness phản ánh PostgreSQL, Kafka, Redis, ClickHouse, Neo4j và MinIO.
- Production mode không trả mock data khi database lỗi.

### Tiêu chí nghiệm thu

- Restart backend không để task hoặc consumer treo.
- Readiness trả 503 khi dependency bắt buộc không sẵn sàng.
- Demo mode và integration mode khác nhau và được test.

## P0.4. Nối payment thật qua Kafka

### Công việc

- Chuẩn hóa payment event với event_id, payment_id, account_id, customer_id, merchant_id, amount, currency, timestamp UTC, schema_version và trace_id.
- Provision topic, partition, retention và key strategy.
- Cấu hình producer retry, timeout, idempotence và serialization error handling.
- Dùng service hostname trong Docker.
- Bổ sung JDBC driver/dependency cần cho Spark.
- Dùng checkpoint location bền vững, không dùng /tmp cho production.
- Ghi raw payment và derived result theo flow idempotent.
- Deduplicate theo event_id/payment_id.

### Tiêu chí nghiệm thu

- Một payment vào Kafka xuất hiện đúng một lần trong database.
- Restart processor không mất event hoặc tạo duplicate.
- Consumer lag và failed messages có metrics.
- Có smoke test gửi event và kiểm tra persisted result.

## P0.5. Hoàn thiện fraud/AML alert path

### Công việc

- Kết nối large_amount, velocity và structuring vào cùng pipeline.
- Định nghĩa output chung: alert key, payment/event reference, account, rule, score, severity, decision, explanation.
- Publish alert vào fraud-events hoặc aml-events theo contract.
- Ghi alert bằng upsert/idempotent insert.
- Đưa relationship vào Neo4j với retry và dead-letter handling.
- Redis velocity phải emit alert event, không chỉ print.
- Gọi thực sự large_amount hiện đang chỉ được import.

### Tiêu chí nghiệm thu

- Mỗi rule có unit test case dương, âm và boundary.
- Vi phạm rule tạo record PENDING trong alerts.
- Alert truy ngược được về payment/event gốc.
- Retry không tạo duplicate alert.

## P0.6. Authentication và authorization

### Công việc

- Bắt buộc JWT secret hợp lệ.
- Validate đầy đủ JWT claims và kiểm tra user còn active.
- Đổi CORS wildcard thành allowlist origin.
- Giới hạn endpoint TPS cho ADMIN/operator.
- Kiểm tra ownership và role khi update/assign alert hoặc upload evidence.
- Dùng enum/whitelist cho status và field update.
- Thêm login throttling và audit login failure.
- Ưu tiên secure HttpOnly cookie thay cho token dài hạn trong localStorage.

### Tiêu chí nghiệm thu

- Analyst chỉ xem/sửa alert đúng phạm vi.
- User không sửa được alert ngoài quyền.
- ADMIN-only endpoints được test với ADMIN, ANALYST và anonymous.
- CORS preflight hoạt động đúng với Authorization.

## P0.7. Evidence upload và storage

### Công việc

- Tách presigned upload và download URL.
- Dùng presigned GET cho download, không dùng MinIO console URL.
- Sanitize filename và chặn path traversal/overwriting ngoài alert scope.
- Lưu object key, MIME type, size, checksum, uploader và timestamps.
- Validate content type, extension và size.
- Kiểm tra quyền trên alert trước khi cấp URL.

### Tiêu chí nghiệm thu

- Không upload được evidence cho alert ngoài quyền.
- Download dùng URL có thời hạn.
- File lỗi MIME, quá lớn hoặc filename nguy hiểm bị từ chối.

## P0.8. Đồng bộ batch/DWH schema

### Công việc

- Chọn source of truth: PostgreSQL warehouse hoặc ClickHouse warehouse.
- Đồng bộ customer_pipeline.py, warehouse_pipeline.py và warehouse/ddl/02_data_warehouse.sql.
- Quyết định PII nào được mask ở Silver/Gold.
- Đồng bộ các cột email, phone, address, city hoặc loại khỏi DataFrame.
- Sửa JDBC URL dùng service name trong container.
- Tạo ClickHouse table với engine, partition và order key rõ ràng nếu ClickHouse là Gold.
- Đảm bảo dimension load idempotent và có SCD Type 2 nếu cần.

### Tiêu chí nghiệm thu

- Customer pipeline chạy thành công từ database rỗng tới Silver.
- Warehouse pipeline đọc Silver và ghi Gold.
- Có schema validation trước pipeline.

## P0.9. Sửa Airflow DAG

### Công việc

- Mount data_quality, fraud, streaming và thư mục cần thiết hoặc dùng SparkSubmitOperator.
- Tạo Airflow image có dependency đúng.
- Sửa toàn bộ host/port theo Docker network.
- DQ task phải trả non-zero exit code khi fail.
- Tách mock retraining khỏi retraining thật.
- Thêm sensor readiness, retry/backoff và timeout.

### Tiêu chí nghiệm thu

- DAG parse thành công.
- DAG chạy được trên container mới.
- DQ fail thì warehouse downstream không chạy.
- Logs có context và error rõ ràng.

---

# P1 — Tăng độ tin cậy, bảo mật và khả năng vận hành

## P1.1. Reliability cho Kafka và Spark

- Thiết kế retry topic và dead-letter topic.
- Định nghĩa retention, replication factor và partition key.
- Dùng event-time UTC, watermark và late-event policy rõ ràng.
- Xử lý malformed JSON và schema mismatch.
- Thêm schema registry hoặc schema version validation.
- Không dùng collect() trong foreachBatch cho dữ liệu lớn.
- Dùng Redis pipeline/atomic Lua/sorted set cho velocity window.
- Đặt checkpoint trên volume bền vững.
- Thêm backpressure và memory limits.

## P1.2. Data quality và data contracts

- Thay mock DataFrame bằng Silver data thật.
- Expectation suite cho not-null, unique key, amount non-negative, enum, timestamp, referential integrity, duplicate rate và PII masking.
- Lưu DQ result theo batch/run ID.
- Publish DQ metrics.
- Có quarantine path cho record lỗi.
- Thêm contract tests producer-processor-sink.

## P1.3. Alert lifecycle và case management

State machine chuẩn:

    PENDING → INVESTIGATING → RESOLVED
                         └──→ IGNORED

- Chỉ cho phép transition hợp lệ.
- Lưu history của status, assignee, note và evidence.
- Dùng optimistic locking/version column.
- Pagination/filter server-side.
- Search theo account, payment, rule, status, date range và risk level.

## P1.4. ML governance

- Bỏ feature random trong fraud engine.
- Xây feature pipeline từ velocity, amount deviation, device, location, profile và graph.
- Split dữ liệu theo thời gian để tránh leakage.
- Đo precision, recall, PR-AUC, false positive rate và calibration.
- Lưu model version, feature schema, dataset hash và metrics.
- Dùng model registry/artifact store thật.
- Có threshold versioning, rollback, drift monitoring và performance monitoring.

## P1.5. Neo4j và AML

- Tạo uniqueness constraint cho customer/account/merchant.
- Tránh relationship duplicate bằng MERGE/idempotency.
- Lưu timestamp, currency và source event ID trên relationship.
- Query cycle theo thời gian và amount threshold.
- Đồng bộ graph alert vào alert lifecycle.
- Retry khi Neo4j unavailable và replay từ Kafka.
- Test cycle 3, 4, 5 nodes và false positives.

## P1.6. Observability

- Structured JSON logs.
- Trace ID, event ID và payment ID xuyên suốt pipeline.
- Metrics cho Kafka throughput/lag, Spark batch, alerts by rule/status/severity, DB latency, WebSocket failures, DQ và model inference.
- Sửa Prometheus targets không expose metrics thực.
- Thêm Grafana panels cho SLO và business metrics.
- Alert khi dependency down, lag tăng, DQ fail hoặc error rate tăng.

## P1.7. API và frontend hardening

- Đưa backend base URL/WebSocket URL vào runtime config.
- Chuẩn hóa loading/error/empty state.
- Backend luôn là nơi quyết định role, không chỉ dựa frontend.
- Pagination và debounce cho tìm kiếm.
- Lazy loading theo tab và manualChunks để giảm bundle.
- Thêm lint, type/schema validation.
- Review ArchitectureTab.jsx vì thay đổi hiện tại mô tả hệ thống khác với banking platform.

## P1.8. CI/CD và dependency hygiene

- CI chạy Python syntax/lint/type checks, pytest, migration checks, frontend build/test, Docker build và Compose smoke test.
- Ignore và remove generated node_modules, .vite, dist, cache.
- Pin dependency versions, CVE scan và controlled upgrades.
- Không pip install package lúc container khởi động.
- Changelog và migration release notes.

---

# P2 — Tối ưu, mở rộng và chuẩn bị production scale

## P2.1. High availability và scale

- Kafka nhiều broker với replication.
- Spark driver/executor deployment riêng.
- Scale consumer theo partition/consumer group.
- Backend replicas sau reverse proxy/load balancer.
- WebSocket qua pub/sub hoặc gateway phù hợp.
- PostgreSQL connection pooler, backup và read replica nếu cần.
- ClickHouse partition/order key theo workload.
- Redis persistence/replication phù hợp.

## P2.2. Security nâng cao

- Vault/KMS/secret manager.
- TLS cho HTTP, Kafka, PostgreSQL, Redis, Neo4j và object storage.
- Network policy thay cho chỉ Docker bridge network.
- RBAC chi tiết theo resource/action.
- MFA/SSO cho investigator.
- Audit log bất biến và retention policy.
- Data retention, deletion và masking theo classification.
- SAST, DAST, dependency/container scanning và penetration test.

## P2.3. Disaster recovery và vận hành

- Backup/restore tự động cho PostgreSQL, ClickHouse metadata, Neo4j và MinIO.
- Kiểm thử restore định kỳ.
- Định nghĩa RPO/RTO theo datastore.
- Runbook cho Kafka lag, database failure, checkpoint corruption, MinIO outage và model rollback.
- Canary deployment và rollback tự động.
- Load test và chaos test.

## P2.4. Fraud/AML nâng cao

- Kết hợp rules, supervised model và graph scoring.
- Entity resolution và case clustering.
- Investigator feedback làm nguồn nhãn.
- Multi-account/customer/merchant risk aggregation.
- Sanctions/PEP screening khi có nguồn dữ liệu phù hợp.
- Explainability dựa trên feature/rule thật, không random text.
- Rule version, approval, effective date và rollback.

## P2.5. Data platform governance

- Catalog dataset, owner, SLA và lineage.
- Định nghĩa Bronze/Silver/Gold chính thức.
- Retention theo loại dữ liệu.
- DQ scorecard theo domain.
- Chuẩn hóa timezone, currency conversion và decimal precision.
- Reconciliation giữa core banking, Kafka, PostgreSQL và ClickHouse.
- Schema evolution policy và compatibility rules.

## P2.6. Sản phẩm và dashboard

- Dashboard điều tra theo workflow thực tế.
- Bulk assignment/status action có audit.
- Saved filters, subscriptions và notification preferences.
- Export có pagination, limit và PII masking.
- KYC 360 dùng dữ liệu thật thay vì random devices/transactions/network.
- Hiển thị data freshness và source status trên widget.
- Accessibility, localization và responsive layout.

---

# 3. Thứ tự triển khai đề xuất

## Sprint 1 — Bootstrap và schema

1. Chốt data contracts.
2. Hoàn thiện configuration/secrets.
3. Tạo migrations cho users/rules/alerts.
4. Sửa Compose healthchecks, dependency và service names.
5. Viết smoke test backend/database.

## Sprint 2 — Event processing

1. Chuẩn hóa Kafka topics và payment event.
2. Chạy producer/consumer thật trong Compose.
3. Hoàn thiện payment persistence và deduplication.
4. Kết nối fraud/AML rules tới alert sink.
5. Viết unit/integration tests cho từng rule.

## Sprint 3 — Batch và warehouse

1. Đồng bộ DWH schema với customer/warehouse pipeline.
2. Sửa MinIO/Spark/Airflow networking.
3. Chạy DQ trên Silver thật.
4. Thêm retry, quarantine và run metadata.
5. Xác nhận dữ liệu truy vấn được từ dashboard.

## Sprint 4 — Security và operations

1. Hoàn thiện authorization và audit trail.
2. Sửa evidence workflow.
3. Thêm health/readiness, metrics và alerting.
4. Tách mock mode khỏi integration mode.
5. Chạy security test và end-to-end test.

## Sprint 5 trở đi — P1/P2

1. Reliability và scale Kafka/Spark.
2. ML governance và model lifecycle.
3. HA, backup/restore và disaster recovery.
4. Security nâng cao và compliance.
5. Tối ưu dashboard và nghiệp vụ fraud/AML.

---

# 4. Definition of Done cấp dự án

Dự án hoàn thành P0 khi:

- docker compose up khởi động được dependency cần thiết;
- migration chạy được từ volume rỗng và volume đã tồn tại;
- user đăng nhập bằng credentials được cấu hình;
- producer gửi payment event thật vào Kafka;
- processor lưu payment và tạo alert thật;
- alert xuất hiện trên dashboard qua API/WebSocket;
- fraud/AML rules có test deterministic;
- batch và DQ chạy trên dữ liệu thật;
- không có hardcoded localhost sai ngữ cảnh container;
- không có mock fallback âm thầm trong integration/production;
- có health check, logs và metrics;
- có test authorization và duplicate event handling.

Dự án chỉ production-ready sau P1 và sau khi có backup/restore test, security review, load test và runbook vận hành.
