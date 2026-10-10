import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useDatasetContext } from './DatasetContext';

export default function AnalyticsTab() {
  const { datasetId, dataset } = useDatasetContext();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState('');
  const graphContainerRef = useRef(null);
  const [graphWidth, setGraphWidth] = useState(800);
  const [graphSource, setGraphSource] = useState('');
  const [moneyFlow, setMoneyFlow] = useState([]);
  const [fraudSequences, setFraudSequences] = useState([]);
  const [insightError, setInsightError] = useState('');

  useEffect(() => {
    if (datasetId !== 'live' && datasetId !== 'ds3_paysim') {
      setGraphData({ nodes: [], links: [] });
      setGraphSource('');
      setGraphLoading(false);
      setGraphError('');
      return undefined;
    }
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    const loadGraph = async () => {
      const endpoint = datasetId === 'ds3_paysim' ? '/api/graph/benchmark' : '/api/graph/circular';
      const response = await fetch(baseUrl + endpoint);
      if (!response.ok) throw new Error('Không tải được AML graph');
      const graph = await response.json();
      if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.links)) {
        throw new Error('Định dạng AML graph không hợp lệ');
      }
      if (datasetId === 'ds3_paysim') setGraphSource('PaySim — synthetic simulation');
      else setGraphSource(graph.nodes.length ? 'Transfer events' : '');
      return graph;
    };
    loadGraph()
      .then(setGraphData)
      .catch(err => setGraphError(err.message))
      .finally(() => setGraphLoading(false));
  }, [datasetId]);

  useEffect(() => {
    if (datasetId !== 'ds3_paysim') {
      setMoneyFlow([]);
      setFraudSequences([]);
      setInsightError('');
      return undefined;
    }
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    Promise.all([
      fetch(baseUrl + '/api/graph/money-flow'),
      fetch(baseUrl + '/api/graph/fraud-sequences'),
    ])
      .then(async ([flowResponse, chainResponse]) => {
        if (!flowResponse.ok || !chainResponse.ok) throw new Error('Không tải được PaySim graph analytics');
        const [flow, chainResult] = await Promise.all([flowResponse.json(), chainResponse.json()]);
        if (!Array.isArray(flow) || !Array.isArray(chainResult?.sequences)) {
          throw new Error('Định dạng PaySim graph analytics không hợp lệ');
        }
        setMoneyFlow(flow);
        setFraudSequences(chainResult.sequences);
      })
      .catch(err => setInsightError(err.message));
  }, [datasetId]);

  useEffect(() => {
    if (!graphContainerRef.current) return undefined;
    const updateWidth = () => setGraphWidth(graphContainerRef.current?.offsetWidth || 0);
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  if (datasetId !== 'live' && datasetId !== 'ds3_paysim') {
    return (
      <div className="panel dataset-not-applicable" role="status">
        <h2 className="panel-title">AML Network không áp dụng cho {dataset.label}</h2>
        <p>{dataset.description}</p>
        <p>Chọn DS3 — PaySim hoặc Live để xem network analytics.</p>
      </div>
    );
  }

  return (
    <div className="grid">
      <div className="panel col-span-12" style={{height: '450px'}}>
        <h2 className="panel-title">AML Network (Neo4j)</h2>
        {graphSource && <div className="dataset-provenance">Nguồn: {graphSource}</div>}
        <div ref={graphContainerRef} style={{width: '100%', height: '380px', overflow: 'hidden'}}>
          {graphData.nodes.length > 0 ? (
            <ForceGraph2D
              width={graphWidth}
              height={380}
              graphData={graphData}
              nodeLabel="name"
              nodeColor={node => node.group === 1 ? '#ef4444' : (node.group === 2 ? '#f59e0b' : '#3b82f6')}
              nodeRelSize={6}
              linkColor={() => '#4b5563'}
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
            />
          ) : (
            <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#94a3b8'}}>
              {graphError ? <span role="alert">{graphError}</span> : graphLoading ? 'Đang tải AML graph...' : 'Chưa có quan hệ AML trong nguồn dữ liệu.'}
            </div>
          )}
        </div>
      </div>
      {datasetId === 'ds3_paysim' && <div className="panel col-span-6">
        <h2 className="panel-title">PaySim money flow</h2>
        <div className="dataset-provenance">Nguồn: PaySim — synthetic simulation</div>
        {moneyFlow.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={moneyFlow} margin={{ top: 12, right: 16, left: 8, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="transaction_type" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #334155' }} />
              <Bar dataKey="total_amount" name="Total amount" fill="#3b82f6" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <div className="dataset-empty">{insightError || 'Chưa có money-flow benchmark.'}</div>}
      </div>}
      {datasetId === 'ds3_paysim' && <div className="panel col-span-6">
        <h2 className="panel-title">TRANSFER → CASH_OUT sequences</h2>
        <div className="dataset-provenance">Adjacent source rows · same step/amount · không có participant link</div>
        {fraudSequences.length ? (
          <div className="dataset-table-wrap">
            <table className="dataset-table">
              <thead><tr><th>Rows</th><th>Transfer path</th><th>Cash-out path</th><th>Amount</th><th>Linked?</th><th>Label</th></tr></thead>
              <tbody>{fraudSequences.map(sequence => (
                <tr key={`${sequence.transfer_event_id}-${sequence.cashout_event_id}`}>
                  <td>{sequence.transfer_source_row} → {sequence.cashout_source_row}</td>
                  <td>{sequence.transfer_origin} → {sequence.transfer_destination}</td>
                  <td>{sequence.cashout_origin} → {sequence.cashout_destination}</td>
                  <td>{Number(sequence.transfer_amount).toLocaleString('vi-VN')}</td>
                  <td>{sequence.participant_linked ? 'có' : 'không'}</td>
                  <td>{sequence.ground_truth_fraud ? 'fraud' : 'normal'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="dataset-empty">{insightError || 'Chưa phát hiện sequence trong phạm vi dữ liệu đã replay.'}</div>}
      </div>}
    </div>
  );
}
