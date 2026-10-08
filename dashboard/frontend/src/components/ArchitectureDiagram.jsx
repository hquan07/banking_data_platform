import React, { useCallback, useEffect, useState } from 'react';
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
  healthy: '#22c55e', unhealthy: '#ef4444', degraded: '#f59e0b',
  documented: '#64748b', planned: '#f59e0b',
};
const statusLabels = {
  healthy: 'Sẵn sàng theo API readiness',
  unhealthy: 'Không phản hồi hoặc probe thất bại',
  degraded: 'API phản hồi nhưng chưa sẵn sàng',
  documented: 'Chưa có health probe trên sơ đồ',
  planned: 'Dataset source chưa được cấu hình',
};

function ArchitectureNode({ data, selected }) {
  const Icon = icons[data.icon] || Server;
  const status = data.health || (data.planned ? 'planned' : 'documented');
  const color = status === 'unhealthy' ? statusColors.unhealthy : data.color;

  return (
    <div style={{
      width: 208, padding: '12px 14px', position: 'relative', cursor: 'pointer',
      borderRadius: 12, color: '#f8fafc', background: 'rgba(30, 41, 59, 0.96)',
      border: `2px ${data.planned ? 'dashed' : 'solid'} ${color}`,
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
      {selected && (
        <div style={{
          position: 'absolute', zIndex: 20, top: 'calc(100% + 10px)', left: 0,
          width: 250, padding: 12, borderRadius: 9, background: '#0f172af5',
          border: '1px solid #475569', boxShadow: '0 12px 28px #000a',
          fontSize: 12, lineHeight: 1.45, color: '#cbd5e1',
        }}>
          <div>{data.description}</div>
          <div style={{ color: statusColors[status], fontWeight: 700, marginTop: 7 }}>{statusLabels[status]}</div>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: '#94a3b8' }} />
    </div>
  );
}

const nodeTypes = { architecture: ArchitectureNode };
const node = (id, x, y, label, sublabel, description, icon, color, planned = false) => ({
  id, type: 'architecture', position: { x, y },
  data: { label, sublabel, description, icon, color, planned, health: planned ? 'planned' : 'documented' },
});

// This is the deployed banking topology, not the NewsPulse services in the visual reference.
const initialNodes = [
  node('payment-producer', 0, 0, 'Dataset source', 'Chưa cấu hình', 'Chưa có dataset replay source được kết nối.', 'database', '#f59e0b', true),
  node('transfer-source', 300, 0, 'Transfer source', 'Chưa cấu hình', 'Chưa có nguồn transfer-events được kết nối.', 'network', '#f59e0b', true),
  node('user', 900, 0, 'Dashboard user', 'Web client', 'Người dùng truy cập giao diện và case management.', 'user', '#3b82f6'),
  node('retry', 0, 145, 'Payment retry worker', 'Approved retry', 'Phát lại payment-events-retry đã được duyệt.', 'retry', '#3b82f6'),
  node('kafka', 300, 145, 'Kafka broker', 'Event streaming + DLQ', 'Truyền payment, transfer, fraud và AML events; giữ retry/DLQ.', 'zap', '#ef4444'),
  node('frontend', 900, 145, 'React dashboard', 'Web + WebSocket', 'Giao diện phân tích, alert và Architecture Map.', 'monitor', '#3b82f6'),
  node('airflow', 0, 290, 'Airflow + DQ', 'Silver orchestration', 'Chạy Silver data quality và lưu run-scoped evidence.', 'server', '#a78bfa'),
  node('spark-payment', 300, 290, 'Spark payment', 'Stream processor', 'Validate schema/event-time và ghi payment ledger.', 'activity', '#f59e0b'),
  node('spark-fraud', 600, 290, 'Spark fraud', 'Rule-based engine', 'Phát hiện fraud bằng rule; chưa có nguồn dataset được kết nối.', 'shield', '#f59e0b'),
  node('backend', 900, 290, 'FastAPI backend', 'Auth + case API', 'Xử lý auth, case lifecycle, analytics và evidence.', 'server', '#3b82f6'),
  node('minio', 0, 435, 'MinIO', 'Silver + evidence', 'Lưu Silver parquet, quarantine và case evidence.', 'archive', '#10b981'),
  node('graph-processor', 300, 435, 'Graph processor', 'AML cycle detection', 'Consumer idempotent; phát hiện chu trình 3–5 tài khoản.', 'graph', '#f59e0b'),
  node('redis', 600, 435, 'Redis', 'Velocity + state', 'Lưu velocity window và trạng thái xử lý.', 'database', '#10b981'),
  node('observability', 900, 435, 'Prometheus + Grafana', 'Metrics + alerts', 'Giám sát metrics, SLO và alert vận hành.', 'bell', '#a78bfa'),
  node('postgres', 300, 580, 'PostgreSQL', 'Ledger + cases', 'Lưu payment, user, alert, audit và DQ runs.', 'database', '#10b981'),
  node('clickhouse', 600, 580, 'ClickHouse', 'OLAP analytics', 'Kho phân tích lịch sử giao dịch.', 'storage', '#10b981'),
  node('neo4j', 900, 580, 'Neo4j', 'AML graph', 'Đồ thị tài khoản và quan hệ chuyển tiền.', 'graph', '#10b981'),
];

const edge = (source, target, label, color, planned = false) => ({
  id: `${source}-${target}`, source, target, label, type: 'smoothstep',
  animated: !planned, style: { stroke: color, strokeWidth: 2, ...(planned ? { strokeDasharray: '6 5' } : {}) },
  markerEnd: { type: MarkerType.ArrowClosed, color },
  labelStyle: { fill: '#f8fafc', fontWeight: 600, fontSize: 11 },
  labelBgStyle: { fill: '#1e293b', fillOpacity: 0.95 },
});

const edges = [
  edge('payment-producer', 'kafka', 'payment-events', '#ef4444'),
  edge('transfer-source', 'kafka', 'transfer-events', '#f59e0b', true),
  edge('retry', 'kafka', 'approved retry', '#ef4444'),
  edge('kafka', 'spark-payment', 'consume', '#ef4444'),
  edge('kafka', 'spark-fraud', 'consume', '#ef4444'),
  edge('kafka', 'graph-processor', 'AML events', '#ef4444'),
  edge('spark-payment', 'postgres', 'payments', '#f59e0b'),
  edge('spark-payment', 'clickhouse', 'analytics', '#f59e0b'),
  edge('spark-fraud', 'redis', 'velocity', '#f59e0b'),
  edge('graph-processor', 'neo4j', 'MERGE edges', '#f59e0b'),
  edge('airflow', 'minio', 'Silver + DQ', '#a78bfa'),
  edge('user', 'frontend', 'browser', '#3b82f6'),
  edge('frontend', 'backend', 'REST + WS', '#3b82f6'),
  edge('backend', 'postgres', 'cases', '#3b82f6'),
  edge('backend', 'clickhouse', 'history', '#3b82f6'),
  edge('backend', 'neo4j', 'AML graph', '#3b82f6'),
  edge('backend', 'minio', 'evidence', '#3b82f6'),
  edge('observability', 'backend', 'scrape', '#a78bfa'),
];

const probedNodes = { backend: 'api', postgres: 'postgres', kafka: 'kafka', redis: 'redis', neo4j: 'neo4j', clickhouse: 'clickhouse', minio: 'minio' };

export default function ArchitectureDiagram() {
  const [nodes, setNodes] = useState(initialNodes);
  const [lastChecked, setLastChecked] = useState(null);
  const onNodesChange = useCallback(changes => setNodes(current => applyNodeChanges(changes, current)), []);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      let result = {};
      try {
        const response = await fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/health/ready`, { cache: 'no-store' });
        const body = await response.json();
        const probes = body.detail || body;
        result = { api: response.ok ? 'healthy' : 'degraded' };
        for (const key of Object.values(probedNodes)) {
          if (key !== 'api' && typeof probes[key] === 'boolean') result[key] = probes[key] ? 'healthy' : 'unhealthy';
        }
      } catch {
        result = { api: 'unhealthy' };
      }
      if (!active) return;
      setNodes(current => current.map(item => {
        const probe = probedNodes[item.id];
        return probe ? { ...item, data: { ...item.data, health: result[probe] || 'documented' } } : item;
      }));
      setLastChecked(new Date());
    };
    checkHealth();
    const timer = window.setInterval(checkHealth, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  return (
    <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, margin: '12px 0 16px', color: '#94a3b8', fontSize: 12 }}>
        <span><span style={{ color: statusColors.healthy }}>●</span> Sẵn sàng (API readiness)</span>
        <span><span style={{ color: statusColors.unhealthy }}>●</span> Probe thất bại</span>
        <span><span style={{ color: statusColors.documented }}>●</span> Chưa có probe</span>
        <span><span style={{ color: statusColors.planned }}>●</span> Chưa tích hợp</span>
        {lastChecked && <span>Kiểm tra lúc {lastChecked.toLocaleTimeString('vi-VN')}</span>}
      </div>
      <div style={{ height: 740, width: '100%', background: '#0b0f19', border: '1px solid #334155', borderRadius: 16, overflow: 'hidden' }}>
        <ReactFlow
          colorMode="dark" nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} nodesConnectable={false}
          fitView fitViewOptions={{ padding: 0.16 }} attributionPosition="bottom-left"
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
          <Controls />
        </ReactFlow>
      </div>
    </>
  );
}
