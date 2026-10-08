import React from 'react';
import ArchitectureDiagram from './ArchitectureDiagram';

// Supporting written map retained alongside the interactive banking topology.
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
      ['Transfer demo generator', 'Sinh transfer-events mô phỏng; chưa có upstream thật'],
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

export default function ArchitectureTab() {
  return (
    <section className="panel col-span-12" aria-label="Kiến trúc banking data platform">
      <h2 className="panel-title">Kiến trúc Banking Data Platform</h2>
      <p style={{ color: '#94a3b8', marginBottom: 0 }}>
        Sơ đồ logic dựa trên cấu hình triển khai. Chọn một service để xem vai trò;
        kéo nút và phóng to/thu nhỏ để khám phá luồng dữ liệu.
      </p>
      <ArchitectureDiagram />
      <h3 style={{ color: '#e2e8f0', marginTop: 32, marginBottom: 20 }}>Các luồng chính</h3>
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
    </section>
  );
}
