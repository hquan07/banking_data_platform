import React, { useState, useEffect, useRef } from 'react';
import { Sankey, Tooltip, ResponsiveContainer, FunnelChart, Funnel, LabelList } from 'recharts';
import ForceGraph2D from 'react-force-graph-2d';

export default function AnalyticsTab({ sankeyData, funnelData }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const graphContainerRef = useRef(null);
  const [graphWidth, setGraphWidth] = useState(800);

  useEffect(() => {
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/graph/circular')
      .then(res => res.json())
      .then(data => {
        if (data && data.nodes) setGraphData(data);
      })
      .catch(err => console.error("Failed to fetch graph data", err));
  }, []);

  useEffect(() => {
    if (graphContainerRef.current) {
      setGraphWidth(graphContainerRef.current.offsetWidth);
      const handleResize = () => setGraphWidth(graphContainerRef.current.offsetWidth);
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, [graphContainerRef.current]);

  return (
    <div className="grid">
      <div className="panel col-span-6" style={{height: '400px'}}>
        <h2 className="panel-title">Money Flow Analysis (Sankey Diagram)</h2>
        <ResponsiveContainer width="100%" height={350}>
          <Sankey
            data={JSON.parse(JSON.stringify(sankeyData))}
            nodePadding={50}
            margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
            link={{ stroke: '#77c878', strokeWidth: '10' }}
            node={{ stroke: '#141a28', strokeWidth: '2' }}
          >
            <Tooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
          </Sankey>
        </ResponsiveContainer>
      </div>

      <div className="panel col-span-6" style={{height: '400px'}}>
        <h2 className="panel-title">Transaction Pipeline Health (Funnel)</h2>
        <ResponsiveContainer width="100%" height={350}>
          <FunnelChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <Tooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
            <Funnel
              dataKey="value"
              data={funnelData}
              isAnimationActive={false}
            >
              <LabelList position="right" fill="#fff" stroke="none" dataKey="name" />
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
      </div>
      
      <div className="panel col-span-12" style={{height: '450px'}}>
        <h2 className="panel-title">AML Network (Neo4j Graph Visualization)</h2>
        <div ref={graphContainerRef} style={{ width: '100%', height: '380px', overflow: 'hidden' }}>
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
              Loading Neo4j graph data...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
