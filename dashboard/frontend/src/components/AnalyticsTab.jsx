import React, { useContext, useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { DATASET_DEFINITIONS } from './DatasetContext';
import { formatNumber, PageHeader, Panel, StateMessage } from './ui';

export default function AnalyticsTab() {
  const { token } = useContext(AuthContext);
  const dataset = DATASET_DEFINITIONS.ds3_paysim;
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [flow, setFlow] = useState([]);
  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const containerRef = useRef(null);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController(); const base = window._env_?.API_URL || 'http://localhost:8000'; setLoading(true); setError('');
    const requestOptions = { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal };
    const requests = [
      fetch(base + '/api/graph/benchmark', requestOptions).then(response => { if (!response.ok) throw new Error('Graph database unavailable'); return response.json(); }),
      fetch(base + '/api/graph/money-flow', requestOptions).then(response => { if (!response.ok) throw new Error('Money-flow analytics unavailable'); return response.json(); }),
      fetch(base + '/api/graph/fraud-sequences', requestOptions).then(response => { if (!response.ok) throw new Error('Fraud-sequence analytics unavailable'); return response.json(); }),
    ];
    Promise.all(requests).then(([graphPayload, flowPayload = [], sequencePayload = { sequences: [] }]) => { setGraph(graphPayload); setFlow(flowPayload); setSequences(sequencePayload.sequences || []); }).catch(fetchError => { if (fetchError.name !== 'AbortError') setError(fetchError.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token]);
  useEffect(() => { const resize = () => setWidth(containerRef.current?.offsetWidth || 800); resize(); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize); }, []);

  return <div className="page-stack">
    <PageHeader eyebrow="Graph intelligence" title="AML Network" description={`${dataset.label} · Phạm vi cố định cho participant graph PaySim.`} />
      <Panel className="col-span-12" title="Transaction network" subtitle="PaySim synthetic BenchmarkAccount graph">
        <div className="graph-canvas" ref={containerRef}>{loading ? <StateMessage type="loading">Đang tải graph…</StateMessage> : error ? <StateMessage type="error">{error}</StateMessage> : graph.nodes.length ? <ForceGraph2D width={width} height={420} graphData={graph} nodeLabel="name" nodeColor={node => node.group === 1 ? '#fb7185' : '#4f8cff'} nodeRelSize={5} linkColor={() => '#334a6d'} linkDirectionalArrowLength={3} linkDirectionalArrowRelPos={1} backgroundColor="#0b1728" /> : <StateMessage>Chưa có quan hệ graph trong phạm vi này.</StateMessage>}</div>
      </Panel>
      <Panel className="col-span-6" title="Money flow by type" subtitle="Tổng amount trên graph PaySim">{flow.length ? <ResponsiveContainer width="100%" height={280}><BarChart data={flow}><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="transaction_type" stroke="#70839e" fontSize={9} /><YAxis stroke="#70839e" fontSize={9} /><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }} /><Bar dataKey="total_amount" name="Total amount" fill="#4f8cff" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer> : <StateMessage>Chưa có money flow.</StateMessage>}</Panel><Panel className="col-span-6" title="Transfer → Cash-out evidence" subtitle="Adjacent source rows, same step và amount; không mặc định participant-linked"><div className="sequence-list">{sequences.slice(0, 8).map(item => <article key={`${item.transfer_event_id}-${item.cashout_event_id}`}><div><strong>{item.transfer_origin} → {item.transfer_destination}</strong><span>{item.cashout_origin} → {item.cashout_destination}</span></div><div><strong>{formatNumber(item.transfer_amount, 2)}</strong><span>{item.participant_linked ? 'Participant linked' : 'Not linked'}</span></div></article>)}</div></Panel>
  </div>;
}
