import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertCircle, Archive, Boxes, CheckCircle2, Clock3, Database,
  GitBranch, HardDrive, Radio, RefreshCw, Server, ShieldCheck, Waves, Zap,
} from 'lucide-react';
import ArchitectureDiagram from './ArchitectureDiagram';
import { Badge, MetricCard, PageHeader, Panel, StateMessage } from './ui';

const services = [
  { key: 'api', name: 'FastAPI', role: 'Auth, cases & analytics API', group: 'Serving', icon: Server },
  { key: 'kafka', name: 'Kafka', role: 'Event backbone & DLQ', group: 'Streaming', icon: Zap },
  { key: 'postgres', name: 'PostgreSQL', role: 'Ledger, cases & benchmark', group: 'Storage', icon: Database },
  { key: 'redis', name: 'Redis', role: 'Velocity state & rule updates', group: 'Storage', icon: Radio },
  { key: 'neo4j', name: 'Neo4j', role: 'Live and benchmark AML graph', group: 'Storage', icon: GitBranch },
  { key: 'clickhouse', name: 'ClickHouse', role: 'Historical OLAP analytics', group: 'Storage', icon: HardDrive },
  { key: 'minio', name: 'MinIO', role: 'Silver data & evidence', group: 'Storage', icon: Archive },
];

const stages = [
  {
    label: 'Event sources',
    tone: 'blue',
    nodes: [
      { name: 'Dataset catalog', meta: 'DS1 · DS3 · DS4', state: 'documented' },
      { name: 'Live producers', meta: 'Not configured', state: 'planned' },
    ],
  },
  {
    label: 'Transport',
    tone: 'red',
    nodes: [
      { name: 'Kafka topics', meta: 'Payment · transfer · benchmark', healthKey: 'kafka' },
      { name: 'Retry & DLQ', meta: 'Controlled replay', state: 'documented' },
    ],
  },
  {
    label: 'Processing',
    tone: 'amber',
    nodes: [
      { name: 'Payment stream', meta: 'Schema · event time · ledger', state: 'documented' },
      { name: 'Fraud evaluation', meta: 'Live + source-aware benchmark', state: 'documented' },
      { name: 'AML graph jobs', meta: 'Separate live / PaySim namespace', state: 'documented' },
    ],
  },
  {
    label: 'Serving & stores',
    tone: 'green',
    nodes: [
      { name: 'FastAPI', meta: 'Dashboard & case workflow', healthKey: 'api' },
      { name: 'Postgres + ClickHouse', meta: 'Operational + analytics', healthKeys: ['postgres', 'clickhouse'] },
      { name: 'Redis + Neo4j + MinIO', meta: 'State · graph · evidence', healthKeys: ['redis', 'neo4j', 'minio'] },
    ],
  },
];

function healthState(node, health) {
  if (node.state) return node.state;
  const keys = node.healthKeys || [node.healthKey];
  const values = keys.map(key => health[key]);
  if (values.every(value => value === true)) return 'healthy';
  if (values.some(value => value === false)) return 'unhealthy';
  return 'unknown';
}

const stateLabel = {
  healthy: 'Ready',
  unhealthy: 'Probe failed',
  unknown: 'Awaiting probe',
  documented: 'No direct probe',
  planned: 'Not integrated',
};

export default function ArchitectureTab() {
  const [health, setHealth] = useState({});
  const [overall, setOverall] = useState('checking');
  const [lastChecked, setLastChecked] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const base = window._env_?.API_URL || 'http://localhost:8000';

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${base}/api/health/ready`, { cache: 'no-store' });
      const body = await response.json();
      const probes = body.detail || body;
      const next = { api: true };
      services.filter(service => service.key !== 'api').forEach(service => {
        next[service.key] = typeof probes[service.key] === 'boolean' ? probes[service.key] : null;
      });
      setHealth(next);
      setOverall(response.ok && probes.status === 'ready' ? 'ready' : 'degraded');
    } catch (healthError) {
      setHealth({ api: false });
      setOverall('offline');
      setError(`Readiness endpoint unavailable: ${healthError.message}`);
    } finally {
      setLastChecked(new Date());
      setLoading(false);
    }
  }, [base]);

  useEffect(() => {
    checkHealth();
    const timer = window.setInterval(checkHealth, 30000);
    return () => window.clearInterval(timer);
  }, [checkHealth]);

  const summary = useMemo(() => {
    const values = services.map(service => health[service.key]).filter(value => typeof value === 'boolean');
    return {
      probed: values.length,
      passing: values.filter(Boolean).length,
      failing: values.filter(value => !value).length,
    };
  }, [health]);

  return <div className="page-stack platform-page">
    <PageHeader
      eyebrow="Runtime control plane"
      title="Kiến trúc Banking Data Platform"
      description="Sơ đồ kiến trúc tương tác, readiness theo thời gian thực và data-flow map của nền tảng banking data."
      actions={<button className="secondary-button" onClick={checkHealth} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} size={14}/> Run probes</button>}
    />
    <MetricCard icon={overall === 'ready' ? <CheckCircle2 size={17}/> : <AlertCircle size={17}/>} label="Platform status" value={overall === 'ready' ? 'Ready' : overall === 'checking' ? 'Checking' : overall === 'offline' ? 'Offline' : 'Degraded'} detail="FastAPI readiness contract" tone={overall === 'ready' ? 'green' : 'red'} />
    <MetricCard icon={<Activity size={17}/>} label="Passing probes" value={`${summary.passing}/${summary.probed || services.length}`} detail="Runtime dependencies responding" tone="green" />
    <MetricCard icon={<ShieldCheck size={17}/>} label="Failed probes" value={summary.failing} detail={summary.failing ? 'Needs operator attention' : 'No dependency failures'} tone={summary.failing ? 'red' : 'blue'} />
    <MetricCard icon={<Clock3 size={17}/>} label="Probe interval" value="30s" detail={lastChecked ? `Checked ${lastChecked.toLocaleTimeString('vi-VN')}` : 'First probe pending'} tone="violet" />

    <Panel className="col-span-12" title="Kiến trúc Banking Data Platform" subtitle="Sơ đồ tương tác của nguồn dữ liệu, streaming, processing, storage, serving và observability">
      <ArchitectureDiagram health={health} lastChecked={lastChecked} />
    </Panel>

    <Panel className="col-span-8" title="Runtime dependencies" subtitle="Các trạng thái bên dưới lấy trực tiếp từ /api/health/ready" action={<Badge tone={overall === 'ready' ? 'green' : 'red'}>{overall}</Badge>}>
      {error && <StateMessage type="error">{error}</StateMessage>}
      <div className="service-health-grid">
        {services.map(service => {
          const Icon = service.icon;
          const state = health[service.key] === true ? 'healthy' : health[service.key] === false ? 'unhealthy' : 'unknown';
          return <article className={`service-health-card state-${state}`} key={service.key}>
            <span className="service-health-icon"><Icon size={16}/></span>
            <div><strong>{service.name}</strong><span>{service.role}</span></div>
            <span className="service-health-status"><i aria-hidden="true" />{service.key === 'api' && state === 'healthy' ? 'Reachable' : stateLabel[state]}</span>
          </article>;
        })}
      </div>
    </Panel>

    <Panel className="col-span-4" title="Health contract" subtitle="Ý nghĩa của từng trạng thái trong tab này">
      <div className="health-contract-list">
        <div><i className="status-healthy"/><span><strong>Ready</strong><small>Probe thực thi thành công ngay lúc kiểm tra.</small></span></div>
        <div><i className="status-unhealthy"/><span><strong>Probe failed</strong><small>Dependency được cấu hình nhưng không sẵn sàng.</small></span></div>
        <div><i className="status-documented"/><span><strong>No direct probe</strong><small>Thành phần có trong topology nhưng readiness API chưa đo.</small></span></div>
        <div><i className="status-planned"/><span><strong>Not integrated</strong><small>Nguồn live bên ngoài chưa được kết nối.</small></span></div>
      </div>
      <div className="health-boundary-note"><Waves size={15}/><p>Platform readiness không đồng nghĩa live events đang chảy. Hiện nguồn payment/transfer bên ngoài vẫn chưa được cấu hình.</p></div>
    </Panel>

    <Panel className="col-span-12" title="Data-flow map" subtitle="Luồng dữ liệu hiện hành; màu trạng thái phân biệt probe thật với thành phần chỉ được mô tả">
      <div className="platform-topology" aria-label="Banking platform data flow">
        {stages.map((stage, stageIndex) => <React.Fragment key={stage.label}>
          <section className={`topology-stage topology-${stage.tone}`}>
            <header><span>0{stageIndex + 1}</span><h3>{stage.label}</h3></header>
            <div className="topology-node-list">
              {stage.nodes.map(node => {
                const state = healthState(node, health);
                return <article className={`topology-node state-${state}`} key={node.name}>
                  <div><strong>{node.name}</strong><span>{node.meta}</span></div>
                  <small><i aria-hidden="true" />{stateLabel[state]}</small>
                </article>;
              })}
            </div>
          </section>
          {stageIndex < stages.length - 1 && <div className="topology-connector" aria-hidden="true"><span>→</span></div>}
        </React.Fragment>)}
      </div>
      <div className="topology-footnotes">
        <span><Boxes size={14}/><strong>Benchmark boundary</strong> DS1/DS3/DS4 replay đi qua benchmark-events, không giả làm live production.</span>
        <span><GitBranch size={14}/><strong>Graph boundary</strong> Account và BenchmarkAccount được lưu ở namespace riêng trong Neo4j.</span>
      </div>
    </Panel>
  </div>;
}
