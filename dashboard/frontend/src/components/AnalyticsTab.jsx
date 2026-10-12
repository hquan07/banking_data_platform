import React, { useContext, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { GitBranch, Search } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { DATASET_DEFINITIONS } from './DatasetContext';
import { Badge, formatNumber, PageHeader, Panel, StateMessage } from './ui';

function graphFromPaths(paths) {
  const nodes = new Map();
  const links = new Map();
  paths.forEach(path => {
    path.nodes.forEach(node => nodes.set(node.id, { id: node.id, name: node.display_id, group: 1 }));
    path.edges.forEach(edge => links.set(edge.event_id, {
      source: edge.source, target: edge.target, value: edge.amount,
      event_id: edge.event_id, relative_step: edge.relative_step,
      risk_score: edge.risk_score, transaction_type: edge.transaction_type,
    }));
  });
  return { nodes: [...nodes.values()], links: [...links.values()] };
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Graph request failed (${response.status})`);
  }
  return response.json();
}

export default function AnalyticsTab() {
  const { token } = useContext(AuthContext);
  const dataset = DATASET_DEFINITIONS.ds3_paysim;
  const initialContext = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return { account: params.get('account'), event: params.get('event'), run: params.get('run') };
  }, []);
  const [anchorEvent, setAnchorEvent] = useState(initialContext.event);
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [paths, setPaths] = useState([]);
  const [flow, setFlow] = useState([]);
  const [sequences, setSequences] = useState([]);
  const [filters, setFilters] = useState({ stepFrom: '', stepTo: '', hops: '2', minRisk: '0' });
  const [applied, setApplied] = useState(filters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const containerRef = useRef(null);
  const [width, setWidth] = useState(800);
  const isEvidenceView = Boolean(initialContext.run && (anchorEvent || initialContext.account));

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    const base = window._env_?.API_URL || 'http://localhost:8000';
    const requestOptions = { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal };
    const bounded = new URLSearchParams({ min_risk_score: applied.minRisk || '0' });
    if (applied.stepFrom !== '' && applied.stepTo !== '') {
      bounded.set('step_from', applied.stepFrom); bounded.set('step_to', applied.stepTo);
    }
    if (initialContext.run) bounded.set('run_id', initialContext.run);
    setLoading(true); setError('');

    let graphRequest;
    if (isEvidenceView) {
      const evidenceParams = new URLSearchParams(bounded);
      evidenceParams.set('hop_count', applied.hops);
      evidenceParams.set('limit', '40');
      if (anchorEvent) evidenceParams.set('event_id', anchorEvent);
      else evidenceParams.set('account_id', initialContext.account);
      graphRequest = fetchJson(`${base}/api/graph/evidence?${evidenceParams}`, requestOptions)
        .then(payload => { setPaths(payload.paths || []); return graphFromPaths(payload.paths || []); });
    } else {
      const graphParams = new URLSearchParams(bounded); graphParams.set('limit', '500');
      if (initialContext.account) graphParams.set('account_id', initialContext.account);
      graphRequest = fetchJson(`${base}/api/graph/benchmark?${graphParams}`, requestOptions)
        .then(payload => { setPaths([]); return payload; });
    }
    const flowParams = new URLSearchParams(); if (initialContext.run) flowParams.set('run_id', initialContext.run);
    const sequenceParams = new URLSearchParams(bounded); sequenceParams.set('limit', '100');
    Promise.all([
      graphRequest,
      fetchJson(`${base}/api/graph/money-flow?${flowParams}`, requestOptions),
      fetchJson(`${base}/api/graph/fraud-sequences?${sequenceParams}`, requestOptions),
    ]).then(([graphPayload, flowPayload = [], sequencePayload = { sequences: [] }]) => {
      setGraph(graphPayload); setFlow(flowPayload); setSequences(sequencePayload.sequences || []);
    }).catch(fetchError => {
      if (fetchError.name !== 'AbortError') setError(fetchError.message);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [anchorEvent, applied, initialContext.account, initialContext.run, isEvidenceView, token]);

  useEffect(() => {
    const resize = () => setWidth(containerRef.current?.offsetWidth || 800);
    resize(); window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const applyFilters = () => {
    const from = filters.stepFrom === '' ? null : Number(filters.stepFrom);
    const to = filters.stepTo === '' ? null : Number(filters.stepTo);
    if ((from === null) !== (to === null)) { setError('Step from và step to phải được nhập cùng nhau.'); return; }
    if (from !== null && (to < from || to - from > 168)) { setError('Relative-step window phải có thứ tự đúng và không vượt quá 168 giờ.'); return; }
    setApplied({ ...filters });
  };

  const focusEvent = eventId => {
    setAnchorEvent(eventId);
    const params = new URLSearchParams(window.location.search); params.set('event', eventId);
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
  };

  const focusedDisplay = initialContext.account?.split(':').at(-1);
  return <div className="page-stack aml-evidence-page">
    <PageHeader eyebrow="Graph intelligence" title="AML Network" description={`${dataset.label} · Bounded participant paths và source-row adjacency evidence.${initialContext.run ? ` Run ${initialContext.run}.` : ''}`} />
    {isEvidenceView && <div className="case-banner case-banner-success" role="status"><GitBranch size={16} /><span>Linked investigation evidence · event {anchorEvent || 'participant anchor'}{initialContext.account ? ` · account ${initialContext.account}` : ''}</span></div>}

    <Panel className="col-span-12" title="Temporal graph controls" subtitle="Tối đa 3 hops · relative-time window tối đa 168 giờ · kết quả luôn có limit">
      <div className="graph-filter-grid">
        <label><span>Step from</span><input type="number" min="0" value={filters.stepFrom} onChange={event => setFilters(value => ({ ...value, stepFrom: event.target.value }))} placeholder="Any" /></label>
        <label><span>Step to</span><input type="number" min="0" value={filters.stepTo} onChange={event => setFilters(value => ({ ...value, stepTo: event.target.value }))} placeholder="Any" /></label>
        <label><span>Hop count</span><select value={filters.hops} onChange={event => setFilters(value => ({ ...value, hops: event.target.value }))}><option value="1">1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option></select></label>
        <label><span>Min risk</span><input type="number" min="0" max="100" value={filters.minRisk} onChange={event => setFilters(value => ({ ...value, minRisk: event.target.value }))} /></label>
        <button className="secondary-button" onClick={applyFilters}><Search size={14} /> Apply graph bounds</button>
      </div>
      {error && <StateMessage type="error">{error}</StateMessage>}
    </Panel>

    <Panel className="col-span-12" title="Transaction network" subtitle={isEvidenceView ? "Investigation-scoped participant paths" : "PaySim BenchmarkAccount graph; node IDs remain run-isolated"}>
      <div className="graph-canvas" ref={containerRef}>{loading ? <StateMessage type="loading">Đang tải bounded graph…</StateMessage> : !error && graph.nodes.length ? <ForceGraph2D width={width} height={420} graphData={graph} nodeLabel="name" nodeColor={node => node.name === focusedDisplay ? '#f7b84b' : '#4f8cff'} nodeRelSize={5} linkColor={link => Number(link.risk_score || 0) >= 65 ? '#fb7185' : '#334a6d'} linkDirectionalArrowLength={3} linkDirectionalArrowRelPos={1} backgroundColor="#0b1728" /> : !error ? <StateMessage>Không có edge phù hợp với bounds hiện tại.</StateMessage> : null}</div>
    </Panel>

    {isEvidenceView && <Panel className="col-span-12" title="Participant path evidence" subtitle="Các edge trong path chia sẻ cùng run; mỗi edge giữ source row, relative step và provenance">
      <div className="graph-path-list">{paths.length ? paths.map(path => <article key={path.path_id}>
        <header><div><Badge tone="blue">{path.evidence_basis}</Badge><strong>{path.path_length} hop{path.path_length > 1 ? 's' : ''}</strong></div><span>{path.participant_linked ? 'Participant linked' : 'Not participant linked'}</span></header>
        <div>{path.edges.map(edge => <button key={edge.event_id} className="graph-edge-evidence" onClick={() => focusEvent(edge.event_id)}>
          <span><strong>{edge.transaction_type}</strong><small>{edge.event_id}</small></span>
          <span><strong>Step {edge.relative_step}</strong><small>row {edge.source_row_number}</small></span>
          <span><strong>{formatNumber(edge.amount, 2)}</strong><small>risk {formatNumber(edge.risk_score, 1)}</small></span>
          <span><strong>{edge.source_kind}</strong><small>{edge.source_file || 'legacy edge'}</small></span>
        </button>)}</div>
      </article>) : <StateMessage>Không có participant path trong bounds đã chọn.</StateMessage>}</div>
    </Panel>}

    <Panel className="col-span-6" title="Money flow by type" subtitle={initialContext.run ? 'Run-scoped amount totals' : 'Tổng amount trên graph PaySim'}>{flow.length ? <ResponsiveContainer width="100%" height={280}><BarChart data={flow}><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="transaction_type" stroke="#70839e" fontSize={9} /><YAxis stroke="#70839e" fontSize={9} /><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }} /><Bar dataKey="total_amount" name="Total amount" fill="#4f8cff" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer> : <StateMessage>Chưa có money flow.</StateMessage>}</Panel>
    <Panel className="col-span-6" title="Transfer → Cash-out evidence" subtitle="Source-row adjacency; participant linkage được báo riêng, không suy diễn identity"><div className="sequence-list">{sequences.length ? sequences.slice(0, 8).map(item => <article key={`${item.run_id}-${item.transfer_event_id}-${item.cashout_event_id}`}><div><span className="sequence-basis"><Badge tone="amber">{item.evidence_basis}</Badge>{item.participant_linked ? <Badge tone="green">Participant linked</Badge> : <Badge tone="neutral">Not linked</Badge>}</span><strong>{item.transfer_origin} → {item.transfer_destination}</strong><span>{item.cashout_origin} → {item.cashout_destination}</span></div><div><strong>{formatNumber(item.transfer_amount, 2)}</strong><button className="text-button" onClick={() => focusEvent(item.transfer_event_id)}>Open source edge</button></div></article>) : <StateMessage>Không có adjacency evidence trong bounds hiện tại.</StateMessage>}</div></Panel>
  </div>;
}
