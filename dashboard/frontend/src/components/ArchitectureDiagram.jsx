import React, { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow, Background, Controls, MarkerType, Handle, Position,
  applyNodeChanges, BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Activity, Archive, Bell, Database, GitBranch, HardDrive,
  Monitor, Network, RefreshCw, Server, Shield, User, Zap,
} from 'lucide-react';

const icons = {
  activity: Activity, archive: Archive, bell: Bell, database: Database,
  graph: GitBranch, storage: HardDrive, monitor: Monitor, network: Network,
  retry: RefreshCw, server: Server, shield: Shield, user: User, zap: Zap,
};

const statusColors = {
  healthy: '#22c55e', unhealthy: '#ef4444', documented: '#64748b', planned: '#f59e0b',
  inactive: '#f59e0b', ondemand: '#60a5fa',
};

const statusLabels = {
  healthy: 'Sẵn sàng theo API readiness',
  unhealthy: 'Không phản hồi hoặc probe thất bại',
  documented: 'Chưa có health probe trên sơ đồ',
  planned: 'Chưa tích hợp',
  inactive: 'Container có mặt nhưng data flow chưa cấu hình',
  ondemand: 'Chỉ chạy khi operator chủ động kích hoạt',
};

function ArchitectureNode({ data, selected }) {
  const Icon = icons[data.icon] || Server;
  const status = data.health || data.status || 'documented';
  const color = status === 'unhealthy' ? statusColors.unhealthy : data.color;

  return <div style={{
    width: 208, padding: '12px 14px', position: 'relative', cursor: 'pointer',
    borderRadius: 12, color: '#f8fafc', background: 'rgba(30, 41, 59, 0.96)',
    border: `2px ${['planned', 'inactive', 'ondemand'].includes(status) ? 'dashed' : 'solid'} ${color}`,
    boxShadow: selected ? `0 0 0 3px ${color}55, 0 12px 28px #0008` : '0 5px 16px #0005',
  }}>
    <Handle type="target" position={Position.Top} style={{ background: '#94a3b8' }} />
    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
      <span style={{ display: 'flex', padding: 8, borderRadius: 8, background: '#ffffff17' }}>
        <Icon size={20} color={color} aria-hidden="true" />
      </span>
      <span style={{ minWidth: 0 }}>
        <strong style={{ display: 'block', fontSize: 13, lineHeight: 1.25 }}>{data.label}</strong>
        <small style={{ display: 'block', color: '#cbd5e1', fontSize: 11, marginTop: 3 }}>{data.sublabel}</small>
      </span>
    </div>
    <span title={statusLabels[status]} aria-label={statusLabels[status]} style={{
      position: 'absolute', top: -7, right: -7, width: 15, height: 15,
      borderRadius: '50%', background: statusColors[status], border: '2px solid #0b0f19',
      boxShadow: status === 'healthy' ? `0 0 9px ${statusColors.healthy}` : 'none',
    }} />
    {selected && <div style={{
      position: 'absolute', zIndex: 20, top: 'calc(100% + 10px)', left: 0,
      width: 250, padding: 12, borderRadius: 9, background: '#0f172af5',
      border: '1px solid #475569', boxShadow: '0 12px 28px #000a',
      fontSize: 12, lineHeight: 1.45, color: '#cbd5e1',
    }}>
      <div>{data.description}</div>
      <div style={{ color: statusColors[status], fontWeight: 700, marginTop: 7 }}>{statusLabels[status]}</div>
    </div>}
    <Handle type="source" position={Position.Bottom} style={{ background: '#94a3b8' }} />
  </div>;
}

const nodeTypes = { architecture: ArchitectureNode };
const node = (id, x, y, label, sublabel, description, icon, color, status = 'documented') => ({
  id, type: 'architecture', position: { x, y },
  data: { label, sublabel, description, icon, color, status },
});

const initialNodes = [
  node('payment-producer', 0, 0, 'Dataset catalog + replay', 'Opt-in benchmark source', 'Profile và replay DS1, DS3, DS4 vào benchmark-events.', 'database', '#10b981', 'ondemand'),
  node('transfer-source', 300, 0, 'Live event sources', 'Chưa cấu hình', 'Chưa có nguồn payment-events hoặc transfer-events bên ngoài được kết nối.', 'network', '#f59e0b', 'planned'),
  node('retry-submit', 600, 0, 'Approved retry submit', 'On-demand operator tool', 'Gửi envelope đã phê duyệt vào payment-events-retry; không phải producer chạy thường trực.', 'retry', '#64748b', 'ondemand'),
  node('user', 1200, 0, 'Dashboard user', 'Web client', 'Người dùng truy cập giao diện và case management.', 'user', '#3b82f6'),
  node('retry', 150, 150, 'Payment retry worker', 'Retry consumer + producer', 'Đọc payment-events-retry rồi phát lại payment-events hoặc chuyển payment-events-dlq.', 'retry', '#3b82f6'),
  node('kafka', 600, 150, 'Kafka broker', 'Event streaming + DLQ', 'Truyền payment, transfer, benchmark, fraud, AML, retry và DLQ events.', 'zap', '#ef4444'),
  node('frontend', 1200, 150, 'React dashboard', 'Web + WebSocket', 'Giao diện phân tích, alert và Architecture Map.', 'monitor', '#3b82f6'),
  node('spark-payment', 0, 320, 'Spark payment processor', 'payment-events', 'Validate schema/event-time, ghi canonical ledger và OLAP copy.', 'activity', '#f59e0b'),
  node('fraud-engine', 300, 320, 'Spark fraud engine', 'Live payment rules', 'Đọc payment-events, dùng Redis velocity state và phát fraud-events/aml-events.', 'shield', '#f59e0b'),
  node('benchmark-processor', 600, 320, 'Benchmark processor', 'DS1 · DS3 · DS4 rules', 'Đọc benchmark-events, lưu provenance/evaluation và phát fraud-events.', 'shield', '#f59e0b'),
  node('live-graph-processor', 900, 320, 'Live graph processor', 'transfer-events', 'Ghi Account transfer graph và phát AML cycle alerts.', 'graph', '#f59e0b'),
  node('backend', 1200, 320, 'FastAPI backend', 'Auth + cases + stream gateway', 'Consume Kafka để broadcast WebSocket, persist alert và phục vụ analytics/evidence API.', 'server', '#3b82f6'),
  node('airflow', 0, 490, 'Airflow', 'Daily batch orchestration', 'Điều phối customer Silver, DQ fail-closed và warehouse Gold jobs.', 'server', '#a78bfa'),
  node('batch-dq', 300, 490, 'Batch + DQ jobs', 'Silver → quality → Gold', 'Đọc core customer/account và Silver parquet; ghi quarantine, DQ result và Gold dimensions.', 'activity', '#a78bfa'),
  node('spark-cluster', 600, 490, 'Spark master + worker', 'Execution runtime', 'Thực thi payment processor, fraud engine và các Spark batch jobs.', 'server', '#a78bfa'),
  node('benchmark-graph-processor', 900, 490, 'Benchmark graph processor', 'PaySim namespace', 'Ghi BenchmarkAccount graph và phát TRANSFER→CASH_OUT sequence alert.', 'graph', '#f59e0b'),
  node('postgres', 0, 660, 'PostgreSQL', 'Ledger + benchmark + cases', 'Lưu payment, benchmark events/evaluations, alert, audit và DQ runs.', 'database', '#10b981'),
  node('clickhouse', 300, 660, 'ClickHouse', 'OLAP analytics', 'Kho phân tích lịch sử giao dịch.', 'storage', '#10b981'),
  node('redis', 600, 660, 'Redis', 'Velocity + state', 'Lưu velocity window, rule updates và Spark batch metrics.', 'database', '#10b981'),
  node('neo4j', 900, 660, 'Neo4j', 'AML graph', 'Đồ thị Account live và BenchmarkAccount synthetic ở namespace riêng.', 'graph', '#10b981'),
  node('minio', 1200, 660, 'MinIO', 'Silver + evidence', 'Lưu Silver parquet, quarantine và case evidence.', 'archive', '#10b981'),
  node('debezium', 0, 830, 'Debezium Connect', '0 connectors configured', 'Container đang chạy nhưng chưa có CDC connector trong runtime hiện tại.', 'network', '#f59e0b', 'inactive'),
  node('kafka-exporter', 600, 830, 'Kafka Exporter', 'Broker + consumer lag metrics', 'Đọc Kafka metrics và expose cho Prometheus.', 'activity', '#a78bfa'),
  node('prometheus', 900, 830, 'Prometheus', 'Metrics + alert rules', 'Scrape FastAPI và Kafka Exporter; đánh giá operational alerts.', 'bell', '#a78bfa'),
  node('grafana', 1200, 830, 'Grafana', 'Operational dashboards', 'Đọc Prometheus qua PromQL để hiển thị platform metrics.', 'monitor', '#a78bfa'),
  node('superset', 1200, 1000, 'Apache Superset', 'Datasource chưa provision', 'Container BI đang chạy nhưng repository chưa provision database connection/dashboard.', 'monitor', '#f59e0b', 'inactive'),
];

const edge = (source, target, label, color, state = 'configured') => ({
  id: `${source}-${target}`, source, target, label, type: 'smoothstep',
  animated: false,
  style: { stroke: color, strokeWidth: 2, ...(state !== 'configured' ? { strokeDasharray: '6 5' } : {}) },
  markerEnd: { type: MarkerType.ArrowClosed, color },
  labelStyle: { fill: '#f8fafc', fontWeight: 600, fontSize: 11 },
  labelBgStyle: { fill: '#1e293b', fillOpacity: 0.95 },
  data: { state },
});

const edges = [
  edge('payment-producer', 'kafka', 'benchmark-events', '#10b981', 'ondemand'),
  edge('transfer-source', 'kafka', 'payment + transfer', '#f59e0b', 'planned'),
  edge('retry-submit', 'kafka', 'payment-events-retry', '#64748b', 'ondemand'),
  edge('kafka', 'retry', 'payment-events-retry', '#ef4444'),
  edge('retry', 'kafka', 'payment / DLQ', '#ef4444'),
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
  edge('fraud-engine', 'kafka', 'fraud + AML events', '#f59e0b'),
  edge('benchmark-processor', 'postgres', 'events + evaluations', '#f59e0b'),
  edge('benchmark-processor', 'kafka', 'fraud-events / DLQ', '#f59e0b'),
  edge('live-graph-processor', 'neo4j', 'Account graph', '#f59e0b'),
  edge('benchmark-graph-processor', 'neo4j', 'BenchmarkAccount graph', '#f59e0b'),
  edge('benchmark-graph-processor', 'kafka', 'aml-events', '#f59e0b'),
  edge('airflow', 'batch-dq', 'orchestrates', '#a78bfa'),
  edge('spark-cluster', 'spark-payment', 'Spark runtime', '#a78bfa'),
  edge('spark-cluster', 'fraud-engine', 'Spark runtime', '#a78bfa'),
  edge('spark-cluster', 'batch-dq', 'Spark runtime', '#a78bfa'),
  edge('postgres', 'batch-dq', 'core customer + account', '#a78bfa'),
  edge('batch-dq', 'minio', 'Silver + DQ artifacts', '#a78bfa'),
  edge('minio', 'batch-dq', 'Silver input', '#a78bfa'),
  edge('batch-dq', 'postgres', 'DQ result + Gold customer', '#a78bfa'),
  edge('batch-dq', 'clickhouse', 'Gold customer', '#a78bfa'),
  edge('user', 'frontend', 'browser', '#3b82f6'),
  edge('frontend', 'backend', 'REST + WS', '#3b82f6'),
  edge('backend', 'postgres', 'cases', '#3b82f6'),
  edge('backend', 'clickhouse', 'history', '#3b82f6'),
  edge('backend', 'neo4j', 'AML graph', '#3b82f6'),
  edge('backend', 'minio', 'evidence', '#3b82f6'),
  edge('backend', 'redis', 'rules + runtime state', '#3b82f6'),
  edge('postgres', 'debezium', 'CDC source', '#f59e0b', 'inactive'),
  edge('debezium', 'kafka', 'connector chưa cấu hình', '#f59e0b', 'inactive'),
  edge('kafka', 'kafka-exporter', 'broker + group metrics', '#a78bfa'),
  edge('kafka-exporter', 'prometheus', '/metrics', '#a78bfa'),
  edge('backend', 'prometheus', '/metrics', '#a78bfa'),
  edge('prometheus', 'grafana', 'PromQL', '#a78bfa'),
  edge('postgres', 'superset', 'BI datasource', '#f59e0b', 'inactive'),
  edge('clickhouse', 'superset', 'BI datasource', '#f59e0b', 'inactive'),
];

const probedNodes = {
  backend: 'api', postgres: 'postgres', kafka: 'kafka', redis: 'redis',
  neo4j: 'neo4j', clickhouse: 'clickhouse', minio: 'minio',
};

export default function ArchitectureDiagram({ health = {}, lastChecked = null }) {
  const [nodes, setNodes] = useState(initialNodes);
  const onNodesChange = useCallback(changes => setNodes(current => applyNodeChanges(changes, current)), []);
  const visibleNodes = useMemo(() => nodes.map(item => {
    const probe = probedNodes[item.id];
    if (!probe) return item;
    const value = health[probe];
    const status = typeof value === 'boolean' ? (value ? 'healthy' : 'unhealthy') : 'documented';
    return { ...item, data: { ...item.data, health: status } };
  }), [health, nodes]);

  return <>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, margin: '12px 0 16px', color: '#94a3b8', fontSize: 12 }}>
      <span><span style={{ color: statusColors.healthy }}>●</span> Sẵn sàng (API readiness)</span>
      <span><span style={{ color: statusColors.unhealthy }}>●</span> Probe thất bại</span>
      <span><span style={{ color: statusColors.documented }}>●</span> Chưa có probe</span>
      <span><span style={{ color: statusColors.planned }}>●</span> Chưa tích hợp</span>
      <span><span style={{ color: statusColors.inactive }}>◆</span> Service có mặt, data flow chưa cấu hình</span>
      <span><span style={{ color: statusColors.ondemand }}>◇</span> On-demand</span>
      {lastChecked && <span>Kiểm tra lúc {lastChecked.toLocaleTimeString('vi-VN')}</span>}
    </div>
    <div style={{ height: 900, width: '100%', background: '#0b0f19', border: '1px solid #334155', borderRadius: 16, overflow: 'hidden' }}>
      <ReactFlow
        colorMode="dark" nodes={visibleNodes} edges={edges} nodeTypes={nodeTypes}
        onNodesChange={onNodesChange} nodesConnectable={false}
        fitView fitViewOptions={{ padding: 0.16 }} attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  </>;
}
