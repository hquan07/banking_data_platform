import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function AnalyticsTab() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState('');
  const graphContainerRef = useRef(null);
  const [graphWidth, setGraphWidth] = useState(800);
  const [graphSource, setGraphSource] = useState('');
  const [moneyFlow, setMoneyFlow] = useState([]);
  const [fraudChains, setFraudChains] = useState([]);
  const [insightError, setInsightError] = useState('');

  useEffect(() => {
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    const loadGraph = async () => {
      const benchmarkResponse = await fetch(baseUrl + '/api/graph/benchmark');
      if (!benchmarkResponse.ok) throw new Error('Không tải được AML graph');
      const benchmark = await benchmarkResponse.json();
      if (!benchmark || !Array.isArray(benchmark.nodes) || !Array.isArray(benchmark.links)) {
        throw new Error('Định dạng AML graph không hợp lệ');
      }
      if (benchmark.nodes.length > 0) {
        setGraphSource('PaySim — synthetic simulation');
        return benchmark;
      }
      const liveResponse = await fetch(baseUrl + '/api/graph/circular');
      if (!liveResponse.ok) throw new Error('Không tải được AML graph');
      const live = await liveResponse.json();
      if (!live || !Array.isArray(live.nodes) || !Array.isArray(live.links)) {
        throw new Error('Định dạng AML graph không hợp lệ');
      }
      setGraphSource(live.nodes.length ? 'Transfer events' : '');
      return live;
    };
    loadGraph()
      .then(setGraphData)
      .catch(err => setGraphError(err.message))
      .finally(() => setGraphLoading(false));
  }, []);

  useEffect(() => {
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    Promise.all([
      fetch(baseUrl + '/api/graph/money-flow'),
      fetch(baseUrl + '/api/graph/fraud-chains'),
    ])
      .then(async ([flowResponse, chainResponse]) => {
        if (!flowResponse.ok || !chainResponse.ok) throw new Error('Không tải được PaySim graph analytics');
        const [flow, chainResult] = await Promise.all([flowResponse.json(), chainResponse.json()]);
        if (!Array.isArray(flow) || !Array.isArray(chainResult?.chains)) {
          throw new Error('Định dạng PaySim graph analytics không hợp lệ');
        }
        setMoneyFlow(flow);
        setFraudChains(chainResult.chains);
      })
      .catch(err => setInsightError(err.message));
  }, []);

  useEffect(() => {
    if (!graphContainerRef.current) return undefined;
    const updateWidth = () => setGraphWidth(graphContainerRef.current?.offsetWidth || 0);
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

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
      <div className="panel col-span-6">
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
      </div>
      <div className="panel col-span-6">
        <h2 className="panel-title">TRANSFER → CASH_OUT chains</h2>
        <div className="dataset-provenance">Detection không sử dụng ground-truth label</div>
        {fraudChains.length ? (
          <div className="dataset-table-wrap">
            <table className="dataset-table">
              <thead><tr><th>Victim</th><th>Mule</th><th>Exit</th><th>Transfer</th><th>Cash out</th><th>Label</th></tr></thead>
              <tbody>{fraudChains.map(chain => (
                <tr key={`${chain.transfer_event_id}-${chain.cashout_event_id}`}>
                  <td>{chain.victim}</td><td>{chain.mule}</td><td>{chain.exit}</td>
                  <td>{Number(chain.transfer_amount).toLocaleString('vi-VN')}</td>
                  <td>{Number(chain.cashout_amount).toLocaleString('vi-VN')}</td>
                  <td>{chain.ground_truth_fraud ? 'fraud' : 'normal'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="dataset-empty">{insightError || 'Chưa phát hiện chuỗi trong phạm vi dữ liệu đã replay.'}</div>}
      </div>
    </div>
  );
}
