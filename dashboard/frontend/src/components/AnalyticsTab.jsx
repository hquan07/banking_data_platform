import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function AnalyticsTab() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState('');
  const graphContainerRef = useRef(null);
  const [graphWidth, setGraphWidth] = useState(800);
  const [graphSource, setGraphSource] = useState('');

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
    </div>
  );
}
