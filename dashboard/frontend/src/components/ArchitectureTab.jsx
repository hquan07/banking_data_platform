import React, { useCallback, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  applyNodeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Deployment topology, not a live health view. Keep this aligned with docker-compose.yml.
const paths = [
  {
    title: 'Thanh toán & phân tích gian lận',
    nodes: [
      ['Payment producer', 'Sinh sự kiện payment-events v1'],
      ['Kafka', 'payment-events, fraud-events, AML và DLQ'],
      ['Spark payment processor', 'Kiểm tra schema, ghi giao dịch'],
      ['PostgreSQL + ClickHouse', 'Sổ giao dịch và phân tích lịch sử'],
      ['Spark fraud engine', 'Rule-based detection; ML chưa được phê duyệt'],
    ],
  },
  {
    title: 'Chuyển tiền & AML graph',
    nodes: [
      ['Transfer events', 'Nguồn sự kiện cần tích hợp từ hệ thống chuyển tiền'],
      ['Graph processor', 'Consumer idempotent, replay từ Kafka'],
      ['Neo4j', 'Quan hệ tài khoản, vòng chuyển tiền 3–5 nút'],
      ['Dashboard backend', 'Lưu alert thành case có audit trail'],
    ],
  },
  {
    title: 'Điều hành & dữ liệu',
    nodes: [
      ['React dashboard', 'Gọi FastAPI và nhận WebSocket'],
      ['FastAPI', 'Auth, case management, analytics và metrics'],
      ['Redis + PostgreSQL', 'Trạng thái luồng và dữ liệu nghiệp vụ'],
      ['Airflow + MinIO', 'Silver data, DQ result và quarantine'],
      ['Prometheus + Grafana', 'Thu thập và hiển thị metrics/alerts'],
    ],
  },
];

const nodeStyle = (color, planned = false) => ({
  background: '#1e293b',
  color: '#f8fafc',
  border: `2px ${planned ? 'dashed' : 'solid'} ${color}`,
  borderRadius: 10,
  boxShadow: '0 5px 18px rgba(0, 0, 0, 0.25)',
  fontSize: 13,
  fontWeight: 600,
  padding: '12px 14px',
  width: 190,
});

// Matches the running Compose topology. The transfer source is an integration
// boundary, not a service currently deployed by this repository.
const diagramNodes = [
  { id: 'payment-producer', position: { x: 0, y: 20 }, data: { label: 'Payment producer', description: 'Tạo payment-events v1 và giữ event_id ổn định khi retry.' }, style: nodeStyle('#38bdf8') },
  { id: 'transfer-source', position: { x: 0, y: 210 }, data: { label: 'Transfer source (chưa tích hợp)', description: 'Nguồn chuyển tiền thực cần phát transfer-events v1.' }, style: nodeStyle('#f59e0b', true) },
  { id: 'airflow', position: { x: 0, y: 490 }, data: { label: 'Airflow + Data Quality', description: 'Tạo Silver data, lưu DQ result và quarantine.' }, style: nodeStyle('#a78bfa') },
  { id: 'retry', position: { x: 255, y: 20 }, data: { label: 'Payment retry worker', description: 'Phát lại sự kiện đã được duyệt; lỗi không hợp lệ về DLQ.' }, style: nodeStyle('#38bdf8') },
  { id: 'kafka', position: { x: 255, y: 215 }, data: { label: 'Kafka', description: 'payment/transfer/fraud/AML events, retry và DLQ.' }, style: nodeStyle('#ef4444') },
  { id: 'minio', position: { x: 255, y: 490 }, data: { label: 'MinIO', description: 'Silver parquet, kết quả DQ, quarantine và case evidence.' }, style: nodeStyle('#a78bfa') },
  { id: 'spark-payment', position: { x: 510, y: 20 }, data: { label: 'Spark payment processor', description: 'Validate schema và event-time, ghi PostgreSQL + ClickHouse.' }, style: nodeStyle('#f97316') },
  { id: 'spark-fraud', position: { x: 510, y: 215 }, data: { label: 'Spark fraud engine', description: 'Rule-based detection; ML synthetic đã tắt.' }, style: nodeStyle('#f97316') },
  { id: 'graph-processor', position: { x: 510, y: 410 }, data: { label: 'Graph processor', description: 'Consumer idempotent; phát hiện chu trình AML 3–5 tài khoản.' }, style: nodeStyle('#f97316') },
  { id: 'postgres', position: { x: 765, y: 0 }, data: { label: 'PostgreSQL', description: 'Payment ledger, users, cases, audit và DQ run results.' }, style: nodeStyle('#10b981') },
  { id: 'clickhouse', position: { x: 765, y: 145 }, data: { label: 'ClickHouse', description: 'Kho phân tích giao dịch lịch sử.' }, style: nodeStyle('#10b981') },
  { id: 'redis', position: { x: 765, y: 290 }, data: { label: 'Redis', description: 'Velocity window, trạng thái Spark batch và rule cache.' }, style: nodeStyle('#10b981') },
  { id: 'neo4j', position: { x: 765, y: 435 }, data: { label: 'Neo4j', description: 'Đồ thị quan hệ tài khoản và chuyển tiền.' }, style: nodeStyle('#10b981') },
  { id: 'frontend', position: { x: 1020, y: 0 }, data: { label: 'React dashboard', description: 'Case management, analytics, WebSocket và Architecture Map.' }, style: nodeStyle('#60a5fa') },
  { id: 'backend', position: { x: 1020, y: 190 }, data: { label: 'FastAPI backend', description: 'Auth, case lifecycle, analytics, evidence và metrics.' }, style: nodeStyle('#60a5fa') },
  { id: 'prometheus', position: { x: 1020, y: 405 }, data: { label: 'Prometheus → Grafana', description: 'Metrics, alert rules và bảng điều khiển vận hành.' }, style: nodeStyle('#a78bfa') },
];

const edgeStyle = { stroke: '#64748b', strokeWidth: 2 };
const diagramEdges = [
  ['payment-producer', 'kafka', 'payment-events'],
  ['transfer-source', 'kafka', 'transfer-events'],
  ['retry', 'kafka', 'approved retry'],
  ['kafka', 'spark-payment', 'consume'],
  ['kafka', 'spark-fraud', 'consume'],
  ['kafka', 'graph-processor', 'consume'],
  ['spark-payment', 'postgres', 'payments'],
  ['spark-payment', 'clickhouse', 'analytics'],
  ['spark-fraud', 'redis', 'velocity'],
  ['graph-processor', 'neo4j', 'MERGE'],
  ['airflow', 'minio', 'Silver + DQ'],
  ['frontend', 'backend', 'REST + WS'],
  ['backend', 'postgres', 'cases'],
  ['backend', 'clickhouse', 'history'],
  ['backend', 'neo4j', 'AML graph'],
  ['backend', 'minio', 'evidence'],
  ['prometheus', 'backend', 'scrape'],
].map(([source, target, label]) => ({
  id: `${source}-${target}`,
  source,
  target,
  label,
  type: 'smoothstep',
  animated: source === 'transfer-source' ? false : undefined,
  style: source === 'transfer-source' ? { ...edgeStyle, strokeDasharray: '6 4' } : edgeStyle,
  markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
  labelStyle: { fill: '#cbd5e1', fontSize: 10 },
  labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9 },
}));

export default function ArchitectureTab() {
  const [nodes, setNodes] = useState(diagramNodes);
  const [selectedNode, setSelectedNode] = useState(null);
  const onNodesChange = useCallback(changes => setNodes(current => applyNodeChanges(changes, current)), []);

  return (
    <section className="panel col-span-12" aria-label="Kiến trúc banking data platform">
      <h2 className="panel-title">Kiến trúc Banking Data Platform</h2>
      <p style={{ color: '#94a3b8', marginBottom: 24 }}>
        Sơ đồ logic dựa trên cấu hình triển khai. Đây không phải trạng thái sức khỏe thời gian thực.
      </p>
      <div style={{ display: 'grid', gap: 24 }}>
        {paths.map(path => (
          <div key={path.title}>
            <h3 style={{ color: '#e2e8f0', marginBottom: 12 }}>{path.title}</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'stretch', gap: 10 }}>
              {path.nodes.map(([name, description], index) => (
                <React.Fragment key={name}>
                  {index > 0 && <span aria-hidden="true" style={{ alignSelf: 'center', color: '#60a5fa' }}>→</span>}
                  <div style={{ flex: '1 1 180px', maxWidth: 260, padding: 14, border: '1px solid #334155', borderRadius: 8, background: '#1e293b' }}>
                    <strong style={{ color: '#fff' }}>{name}</strong>
                    <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: 0 }}>{description}</p>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </div>
        ))}
      </div>
      <h3 style={{ color: '#e2e8f0', marginTop: 32, marginBottom: 8 }}>Architecture diagram</h3>
      <p style={{ color: '#94a3b8', marginBottom: 12 }}>
        Kéo nút, phóng to/thu nhỏ và chọn service để xem vai trò. Đường nét đứt là nguồn chưa tích hợp; màu sắc không biểu thị health realtime.
      </p>
      <div style={{ height: 680, width: '100%', background: '#0b0f19', border: '1px solid #334155', borderRadius: 12, overflow: 'hidden' }}>
        <ReactFlow
          colorMode="dark"
          nodes={nodes}
          edges={diagramEdges}
          onNodesChange={onNodesChange}
          onNodeClick={(_, node) => setSelectedNode(node)}
          onPaneClick={() => setSelectedNode(null)}
          nodesConnectable={false}
          elementsSelectable
          fitView
          fitViewOptions={{ padding: 0.16 }}
          attributionPosition="bottom-left"
        >
          <Background variant="dots" gap={20} size={1} color="#334155" />
          <MiniMap pannable zoomable nodeColor={node => node.id === 'transfer-source' ? '#f59e0b' : '#3b82f6'} />
          <Controls />
        </ReactFlow>
      </div>
      <div role="status" style={{ minHeight: 70, marginTop: 12, padding: 12, border: '1px solid #334155', borderRadius: 8, color: '#cbd5e1' }}>
        {selectedNode ? <><strong style={{ color: '#fff' }}>{selectedNode.data.label}</strong><div>{selectedNode.data.description}</div></> : 'Chọn một service trong sơ đồ để xem chi tiết.'}
      </div>
    </section>
  );
}
