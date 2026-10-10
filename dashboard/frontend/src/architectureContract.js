export const ARCHITECTURE_VIEWS = [
  { id: 'realtime', label: 'Realtime & Kafka' },
  { id: 'batch', label: 'Batch & DQ' },
  { id: 'serving', label: 'Serving & Ops' },
  { id: 'all', label: 'Toàn bộ' },
];

export const ARCHITECTURE_NODES = [
  { id: 'payment-producer', label: 'Dataset catalog + replay', sublabel: 'Opt-in benchmark source', description: 'Profile và replay DS1, DS3, DS4 vào benchmark-events.', icon: 'database', color: '#10b981', status: 'ondemand' },
  { id: 'transfer-source', label: 'Live event sources', sublabel: 'Chưa cấu hình', description: 'Chưa có nguồn payment-events hoặc transfer-events bên ngoài được kết nối.', icon: 'network', color: '#f59e0b', status: 'planned' },
  { id: 'retry-submit', label: 'Approved retry submit', sublabel: 'On-demand operator tool', description: 'Gửi envelope đã phê duyệt vào payment-events-retry; không phải producer chạy thường trực.', icon: 'retry', color: '#64748b', status: 'ondemand' },
  { id: 'user', label: 'Dashboard user', sublabel: 'Web client', description: 'Người dùng truy cập giao diện và case management.', icon: 'user', color: '#3b82f6' },
  { id: 'retry', label: 'Payment retry worker', sublabel: 'Retry consumer + producer', description: 'Đọc payment-events-retry rồi phát lại payment-events hoặc chuyển payment-events-dlq.', icon: 'retry', color: '#3b82f6' },
  { id: 'kafka', label: 'Kafka broker', sublabel: 'Event streaming + DLQ', description: 'Truyền payment, transfer, benchmark, fraud, AML, retry và DLQ events.', icon: 'zap', color: '#ef4444' },
  { id: 'frontend', label: 'React dashboard', sublabel: 'Web + WebSocket', description: 'Giao diện phân tích, alert và Architecture Map.', icon: 'monitor', color: '#3b82f6' },
  { id: 'spark-payment', label: 'Spark payment processor', sublabel: 'payment-events', description: 'Validate schema/event-time, ghi canonical ledger và OLAP copy.', icon: 'activity', color: '#f59e0b' },
  { id: 'fraud-engine', label: 'Spark fraud engine', sublabel: 'Live payment rules', description: 'Đọc payment-events, dùng Redis velocity state và phát fraud-events/aml-events.', icon: 'shield', color: '#f59e0b' },
  { id: 'benchmark-processor', label: 'Benchmark processor', sublabel: 'DS1 · DS3 · DS4 rules', description: 'Đọc benchmark-events, lưu provenance/evaluation và phát fraud-events.', icon: 'shield', color: '#f59e0b' },
  { id: 'live-graph-processor', label: 'Live graph processor', sublabel: 'transfer-events', description: 'Ghi Account transfer graph và phát AML cycle alerts.', icon: 'graph', color: '#f59e0b' },
  { id: 'backend', label: 'FastAPI backend', sublabel: 'Auth + cases + stream gateway', description: 'Consume Kafka để broadcast WebSocket, persist alert và phục vụ analytics/evidence API.', icon: 'server', color: '#3b82f6' },
  { id: 'airflow', label: 'Airflow', sublabel: 'Daily batch orchestration', description: 'Điều phối customer Silver, DQ fail-closed và warehouse Gold jobs.', icon: 'server', color: '#a78bfa' },
  { id: 'batch-dq', label: 'Batch + DQ jobs', sublabel: 'Silver → quality → Gold', description: 'Đọc core customer/account và Silver parquet; ghi quarantine, DQ result và Gold dimensions.', icon: 'activity', color: '#a78bfa' },
  { id: 'spark-cluster', label: 'Spark master + worker', sublabel: 'Execution runtime', description: 'Thực thi payment processor, fraud engine và các Spark batch jobs.', icon: 'server', color: '#a78bfa' },
  { id: 'benchmark-graph-processor', label: 'Benchmark graph processor', sublabel: 'PaySim namespace', description: 'Ghi BenchmarkAccount graph và phát TRANSFER→CASH_OUT sequence alert.', icon: 'graph', color: '#f59e0b' },
  { id: 'postgres', label: 'PostgreSQL', sublabel: 'Ledger + benchmark + cases', description: 'Lưu payment, benchmark events/evaluations, alert, audit và DQ runs.', icon: 'database', color: '#10b981' },
  { id: 'clickhouse', label: 'ClickHouse', sublabel: 'OLAP analytics', description: 'Kho phân tích lịch sử giao dịch và Gold customer dimension.', icon: 'storage', color: '#10b981' },
  { id: 'redis', label: 'Redis', sublabel: 'Velocity + state', description: 'Lưu velocity window, rule updates và Spark batch metrics.', icon: 'database', color: '#10b981' },
  { id: 'neo4j', label: 'Neo4j', sublabel: 'AML graph', description: 'Đồ thị Account live và BenchmarkAccount synthetic ở namespace riêng.', icon: 'graph', color: '#10b981' },
  { id: 'minio', label: 'MinIO', sublabel: 'Silver + evidence', description: 'Lưu Silver parquet, quarantine, DQ result và case evidence.', icon: 'archive', color: '#10b981' },
  { id: 'debezium', label: 'Debezium Connect', sublabel: '0 connectors configured', description: 'Container đang chạy nhưng chưa có CDC connector trong runtime hiện tại.', icon: 'network', color: '#f59e0b', status: 'inactive' },
  { id: 'kafka-exporter', label: 'Kafka Exporter', sublabel: 'Broker + consumer lag metrics', description: 'Đọc Kafka metrics và expose cho Prometheus.', icon: 'activity', color: '#a78bfa' },
  { id: 'prometheus', label: 'Prometheus', sublabel: 'Metrics + alert rules', description: 'Scrape FastAPI và Kafka Exporter; đánh giá operational alerts.', icon: 'bell', color: '#a78bfa' },
  { id: 'grafana', label: 'Grafana', sublabel: 'Operational dashboards', description: 'Đọc Prometheus qua PromQL để hiển thị platform metrics.', icon: 'monitor', color: '#a78bfa' },
  { id: 'superset', label: 'Apache Superset', sublabel: 'Datasource chưa provision', description: 'Container BI đang chạy nhưng repository chưa provision database connection/dashboard.', icon: 'monitor', color: '#f59e0b', status: 'inactive' },
];

export const ARCHITECTURE_LAYOUTS = {
  realtime: {
    'payment-producer': [0, 0], 'transfer-source': [300, 0], 'retry-submit': [600, 0], user: [1200, 0],
    retry: [150, 155], kafka: [600, 155], frontend: [1200, 155],
    'spark-payment': [0, 340], 'fraud-engine': [300, 340], 'benchmark-processor': [600, 340],
    'live-graph-processor': [900, 340], backend: [1200, 340], 'benchmark-graph-processor': [900, 515],
    postgres: [0, 690], clickhouse: [300, 690], redis: [600, 690], neo4j: [900, 690], minio: [1200, 690],
  },
  batch: {
    airflow: [0, 0], 'spark-cluster': [330, 0],
    postgres: [0, 210], 'batch-dq': [330, 210], minio: [660, 210], clickhouse: [990, 210],
  },
  serving: {
    kafka: [0, 0], backend: [300, 0], frontend: [600, 0], user: [900, 0],
    postgres: [0, 210], clickhouse: [240, 210], redis: [480, 210], neo4j: [720, 210], minio: [960, 210],
    'kafka-exporter': [0, 420], prometheus: [300, 420], grafana: [600, 420],
    debezium: [0, 630], superset: [600, 630],
  },
  all: {
    'payment-producer': [0, 0], 'transfer-source': [300, 0], 'retry-submit': [600, 0], user: [1200, 0],
    retry: [150, 150], kafka: [600, 150], frontend: [1200, 150],
    'spark-payment': [0, 320], 'fraud-engine': [300, 320], 'benchmark-processor': [600, 320],
    'live-graph-processor': [900, 320], backend: [1200, 320], airflow: [0, 490], 'batch-dq': [300, 490],
    'spark-cluster': [600, 490], 'benchmark-graph-processor': [900, 490],
    postgres: [0, 660], clickhouse: [300, 660], redis: [600, 660], neo4j: [900, 660], minio: [1200, 660],
    debezium: [0, 830], 'kafka-exporter': [600, 830], prometheus: [900, 830], grafana: [1200, 830], superset: [1200, 1000],
  },
};

const edge = (source, target, label, color, options = {}) => ({
  id: `${source}-${target}`, source, target, label, color, state: 'configured', ...options,
});

export const ARCHITECTURE_EDGES = [
  edge('payment-producer', 'kafka', 'benchmark-events', '#10b981', { state: 'ondemand' }),
  edge('transfer-source', 'kafka', 'payment + transfer', '#f59e0b', { state: 'planned' }),
  edge('retry-submit', 'kafka', 'payment-events-retry', '#64748b', { state: 'ondemand' }),
  edge('kafka', 'retry', 'payment-events-retry', '#ef4444'),
  edge('retry', 'kafka', 'payment / DLQ', '#ef4444', { sourceSide: 'bottom', targetSide: 'bottom' }),
  edge('kafka', 'spark-payment', 'payment-events', '#ef4444'),
  edge('kafka', 'fraud-engine', 'payment-events', '#ef4444'),
  edge('kafka', 'benchmark-processor', 'benchmark-events', '#ef4444'),
  edge('kafka', 'live-graph-processor', 'transfer-events', '#ef4444'),
  edge('kafka', 'benchmark-graph-processor', 'benchmark-events', '#ef4444'),
  edge('kafka', 'backend', 'events → WS + cases', '#ef4444'),
  edge('spark-payment', 'postgres', 'payments', '#f59e0b'),
  edge('spark-payment', 'clickhouse', 'OLAP copy', '#f59e0b'),
  edge('spark-payment', 'redis', 'batch metrics', '#f59e0b'),
  edge('fraud-engine', 'redis', 'velocity + metrics', '#f59e0b'),
  edge('fraud-engine', 'kafka', 'fraud + AML events', '#f59e0b', { sourceSide: 'right', targetSide: 'left' }),
  edge('benchmark-processor', 'postgres', 'events + evaluations', '#f59e0b'),
  edge('benchmark-processor', 'kafka', 'fraud-events / DLQ', '#f59e0b', { sourceSide: 'right', targetSide: 'right' }),
  edge('live-graph-processor', 'neo4j', 'Account graph', '#f59e0b'),
  edge('benchmark-graph-processor', 'neo4j', 'BenchmarkAccount graph', '#f59e0b'),
  edge('benchmark-graph-processor', 'kafka', 'aml-events', '#f59e0b', { sourceSide: 'left', targetSide: 'right' }),
  edge('user', 'frontend', 'browser', '#3b82f6'),
  edge('frontend', 'backend', 'REST + WS', '#3b82f6'),
  edge('backend', 'postgres', 'cases + alerts', '#3b82f6'),
  edge('backend', 'clickhouse', 'history', '#3b82f6'),
  edge('backend', 'neo4j', 'AML graph', '#3b82f6'),
  edge('backend', 'minio', 'evidence', '#3b82f6'),
  edge('backend', 'redis', 'rules + runtime state', '#3b82f6'),
  edge('airflow', 'batch-dq', 'orchestrates', '#a78bfa'),
  edge('spark-cluster', 'spark-payment', 'Spark runtime', '#a78bfa'),
  edge('spark-cluster', 'fraud-engine', 'Spark runtime', '#a78bfa'),
  edge('spark-cluster', 'batch-dq', 'Spark runtime', '#a78bfa'),
  edge('postgres', 'batch-dq', 'core customer + account', '#a78bfa'),
  edge('batch-dq', 'minio', 'Silver + DQ artifacts', '#a78bfa'),
  edge('minio', 'batch-dq', 'Silver input', '#a78bfa', { sourceSide: 'bottom', targetSide: 'bottom' }),
  edge('batch-dq', 'postgres', 'DQ result + Gold customer', '#a78bfa', { sourceSide: 'bottom', targetSide: 'bottom' }),
  edge('batch-dq', 'clickhouse', 'Gold customer', '#a78bfa'),
  edge('postgres', 'debezium', 'CDC source', '#f59e0b', { state: 'inactive' }),
  edge('debezium', 'kafka', 'connector chưa cấu hình', '#f59e0b', { state: 'inactive' }),
  edge('kafka', 'kafka-exporter', 'broker + group metrics', '#a78bfa'),
  edge('kafka-exporter', 'prometheus', '/metrics', '#a78bfa'),
  edge('backend', 'prometheus', '/metrics', '#a78bfa'),
  edge('prometheus', 'grafana', 'PromQL', '#a78bfa'),
  edge('postgres', 'superset', 'BI datasource', '#f59e0b', { state: 'inactive' }),
  edge('clickhouse', 'superset', 'BI datasource', '#f59e0b', { state: 'inactive' }),
];

export function topologyForView(viewId) {
  const layout = ARCHITECTURE_LAYOUTS[viewId] || ARCHITECTURE_LAYOUTS.realtime;
  const nodeIds = new Set(Object.keys(layout));
  return {
    nodes: ARCHITECTURE_NODES.filter(node => nodeIds.has(node.id)).map(node => ({
      ...node, position: { x: layout[node.id][0], y: layout[node.id][1] },
    })),
    edges: ARCHITECTURE_EDGES.filter(item => nodeIds.has(item.source) && nodeIds.has(item.target)),
  };
}
