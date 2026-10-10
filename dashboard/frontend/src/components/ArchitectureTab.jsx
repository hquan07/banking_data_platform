import React from 'react';
import ArchitectureDiagram from './ArchitectureDiagram';
import { PageHeader, Panel } from './ui';

// Supporting written map retained alongside the interactive banking topology.
const paths = [
  {
    title: 'Thanh toán & phân tích gian lận',
    nodes: [
      ['Dataset catalog + replay', 'DS1/DS3/DS4 đã profile; replay benchmark-events theo yêu cầu'],
      ['Kafka', 'payment, transfer, benchmark, fraud, AML và DLQ'],
      ['Spark payment processor', 'Kiểm tra schema, ghi giao dịch'],
      ['Benchmark processor', 'Lưu provenance/evaluation; rule theo từng nguồn'],
      ['PostgreSQL + ClickHouse', 'Benchmark analytics và lịch sử payment'],
    ],
  },
  {
    title: 'Chuyển tiền & AML graph',
    nodes: [
      ['Live event sources', 'Nguồn payment-events và transfer-events bên ngoài vẫn chưa cấu hình'],
      ['Graph processors', 'Live Account và PaySim BenchmarkAccount tách biệt'],
      ['Neo4j', 'Chu trình live + PaySim sequence tách biệt, không giả participant link'],
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
    <div className="page-stack">
      <PageHeader eyebrow="Runtime topology" title="Platform Health" description="Readiness probes và data-flow topology của Banking Data Platform đang triển khai." />
      <Panel className="col-span-12" title="Service topology" subtitle="Chọn service để xem vai trò; kéo node và zoom để khám phá luồng dữ liệu.">
        <ArchitectureDiagram />
      </Panel>
      <Panel className="col-span-12" title="Core data paths" subtitle="Ranh giới giữa benchmark replay, live stream và operational stores">
      <div className="platform-paths">
        {paths.map(path => (
          <article key={path.title}>
            <h3>{path.title}</h3>
            <div className="platform-path">
              {path.nodes.map(([name, description], index) => (
                <React.Fragment key={name}>
                  {index > 0 && <span aria-hidden="true" className="path-arrow">→</span>}
                  <div className="path-node">
                    <strong>{name}</strong>
                    <p>{description}</p>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </article>
        ))}
      </div>
      </Panel>
    </div>
  );
}
