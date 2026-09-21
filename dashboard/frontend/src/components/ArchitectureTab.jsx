import React, { useState, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  applyNodeChanges,
  applyEdgeChanges,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Monitor,
  Server,
  TerminalSquare,
  Database,
  Activity,
  Zap,
  Globe
} from 'lucide-react';

// --- Metrics Data Mock ---
const getMetricsForNode = (nodeId) => {
  const metricsMap = {
    client: { desc: 'React Dashboard', stat: 'Active Sessions: 42' },
    gateway: { desc: 'API Gateway / Nginx', stat: 'Requests: 1,204/s' },
    java: { desc: 'Spring Boot Core', stat: 'CPU: 18% | RAM: 1.2GB' },
    python: { desc: 'FastAPI AI Engine', stat: 'Latency: 15ms' },
    kafka: { desc: 'Apache Kafka', stat: 'Throughput: 12,450 Msg/s' },
    spark: { desc: 'Spark/Flink Streaming', stat: 'Batch Time: 5s' },
    pg: { desc: 'PostgreSQL OLTP', stat: 'Connections: 34/100' },
    ch: { desc: 'ClickHouse OLAP', stat: 'Rows Scanned: 450M' },
    neo: { desc: 'Neo4j Graph', stat: 'Traversal Time: 22ms' },
  };
  return metricsMap[nodeId] || { desc: 'Unknown', stat: 'N/A' };
};

// --- Custom Node Component ---
const CustomNode = ({ id, data }) => {
  const [isHealthy, setIsHealthy] = useState(true);
  const [showMetrics, setShowMetrics] = useState(false);

  // Icons mapping
  const IconMap = {
    monitor: Monitor,
    globe: Globe,
    server: Server,
    terminal: TerminalSquare,
    database: Database,
    activity: Activity,
    zap: Zap,
  };
  const Icon = IconMap[data.icon] || Server;

  const handleDoubleClick = () => setIsHealthy(!isHealthy);
  const handleClick = () => setShowMetrics(!showMetrics);

  const metrics = getMetricsForNode(id);

  return (
    <div
      onDoubleClick={handleDoubleClick}
      onClick={handleClick}
      style={{
        padding: '12px 16px',
        borderRadius: '12px',
        background: isHealthy ? 'rgba(30, 41, 59, 0.9)' : 'rgba(127, 29, 29, 0.9)',
        border: `2px solid ${isHealthy ? data.color || '#475569' : '#ef4444'}`,
        color: '#fff',
        width: '200px',
        boxShadow: isHealthy ? '0 4px 6px -1px rgba(0, 0, 0, 0.3)' : '0 0 15px rgba(239, 68, 68, 0.7)',
        position: 'relative',
        transition: 'all 0.3s ease',
        cursor: 'pointer'
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#94a3b8' }} />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <div style={{ padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px', display: 'flex' }}>
          <Icon size={20} color={isHealthy ? (data.color || '#fff') : '#fff'} />
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: '14px' }}>{data.label}</div>
          <div style={{ fontSize: '11px', color: '#cbd5e1' }}>{data.sublabel}</div>
        </div>
      </div>

      {/* Health Status Indicator */}
      <div style={{
        position: 'absolute', top: '-6px', right: '-6px',
        width: '14px', height: '14px', borderRadius: '50%',
        background: isHealthy ? '#22c55e' : '#ef4444',
        border: '2px solid #0f172a',
        boxShadow: isHealthy ? '0 0 8px #22c55e' : '0 0 8px #ef4444',
        animation: isHealthy ? 'none' : 'pulse 1s infinite'
      }} />

      {/* Metrics Tooltip (Absolute positioned) */}
      {showMetrics && (
        <div style={{
          position: 'absolute', top: '105%', left: 0, width: '100%',
          background: 'rgba(15, 23, 42, 0.95)', border: '1px solid #334155',
          borderRadius: '8px', padding: '10px', fontSize: '12px', zIndex: 50,
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
        }}>
          <div style={{ color: '#94a3b8', marginBottom: '4px' }}>{metrics.desc}</div>
          <div style={{ fontWeight: 'bold', color: '#38bdf8' }}>{metrics.stat}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: '#94a3b8' }} />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

// --- Initial Data ---
const initialNodes = [
  // Layer 1: Client
  { id: 'client', type: 'custom', position: { x: 350, y: 50 }, data: { label: 'React Dashboard', sublabel: 'Client Browser', icon: 'monitor', color: '#3b82f6' } },
  // Layer 2: Gateway
  { id: 'gateway', type: 'custom', position: { x: 350, y: 180 }, data: { label: 'API Gateway', sublabel: 'Nginx / Routing', icon: 'globe', color: '#f59e0b' } },
  // Layer 3: Backend
  { id: 'java', type: 'custom', position: { x: 200, y: 320 }, data: { label: 'Java Spring Boot', sublabel: 'Core API & Auth', icon: 'server', color: '#10b981' } },
  { id: 'python', type: 'custom', position: { x: 500, y: 320 }, data: { label: 'Python FastAPI', sublabel: 'AI & MLOps', icon: 'terminal', color: '#8b5cf6' } },
  // Layer 3: Streaming (Side)
  { id: 'kafka', type: 'custom', position: { x: 800, y: 180 }, data: { label: 'Apache Kafka', sublabel: 'Message Broker', icon: 'activity', color: '#ef4444' } },
  { id: 'spark', type: 'custom', position: { x: 800, y: 320 }, data: { label: 'Spark Streaming', sublabel: 'Stream Processor', icon: 'zap', color: '#ef4444' } },
  // Layer 4: Databases
  { id: 'pg', type: 'custom', position: { x: 200, y: 500 }, data: { label: 'PostgreSQL', sublabel: 'Core OLTP Data', icon: 'database', color: '#334155' } },
  { id: 'neo', type: 'custom', position: { x: 500, y: 500 }, data: { label: 'Neo4j', sublabel: 'Graph & AML', icon: 'database', color: '#334155' } },
  { id: 'ch', type: 'custom', position: { x: 800, y: 500 }, data: { label: 'ClickHouse', sublabel: 'Analytics OLAP', icon: 'database', color: '#334155' } },
];

const defaultEdgeOptions = {
  animated: true,
  markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  style: { strokeWidth: 2, stroke: '#94a3b8' },
  labelStyle: { fill: '#fff', fontWeight: 600, fontSize: 11 },
  labelBgStyle: { fill: '#1e293b', fillOpacity: 0.8 },
};

const initialEdges = [
  // HTTP
  { id: 'e-client-gw', source: 'client', target: 'gateway', label: 'HTTP/REST', ...defaultEdgeOptions, style: { strokeWidth: 2, stroke: '#3b82f6' } },
  { id: 'e-gw-java', source: 'gateway', target: 'java', label: 'HTTP', ...defaultEdgeOptions, style: { strokeWidth: 2, stroke: '#10b981' } },
  { id: 'e-gw-python', source: 'gateway', target: 'python', label: 'HTTP', ...defaultEdgeOptions, style: { strokeWidth: 2, stroke: '#8b5cf6' } },
  
  // Internal
  { id: 'e-java-python', source: 'java', target: 'python', label: 'gRPC', ...defaultEdgeOptions, type: 'step', style: { strokeWidth: 2, stroke: '#8b5cf6', strokeDasharray: '5,5' } },
  
  // Streaming
  { id: 'e-kafka-spark', source: 'kafka', target: 'spark', label: 'Consume', ...defaultEdgeOptions, style: { strokeWidth: 3, stroke: '#ef4444' } },
  { id: 'e-spark-pg', source: 'spark', target: 'pg', label: 'Save', ...defaultEdgeOptions, style: { strokeWidth: 2, stroke: '#ef4444' } },
  { id: 'e-spark-ch', source: 'spark', target: 'ch', label: 'Log', ...defaultEdgeOptions, style: { strokeWidth: 2, stroke: '#ef4444' } },
  
  // DB connections
  { id: 'e-java-pg', source: 'java', target: 'pg', label: 'TCP/SQL', ...defaultEdgeOptions },
  { id: 'e-java-neo', source: 'java', target: 'neo', label: 'Bolt', ...defaultEdgeOptions },
  { id: 'e-java-ch', source: 'java', target: 'ch', label: 'HTTP/JDBC', ...defaultEdgeOptions, type: 'step' },
];

export default function ArchitectureTab() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '24px', margin: '0 0 8px 0', fontWeight: 'bold' }}>Architecture Map</h2>
          <p style={{ color: '#94a3b8', margin: 0 }}>
            Interactive System Topology. <span style={{ color: '#38bdf8' }}>Single-click</span> node to view real-time metrics. <span style={{ color: '#ef4444' }}>Double-click</span> to toggle health status.
          </p>
        </div>
      </div>

      {/* React Flow Canvas container */}
      <div style={{ height: '700px', width: '100%', background: '#0b0f19', borderRadius: '16px', border: '1px solid #1e293b', overflow: 'hidden' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          defaultEdgeOptions={defaultEdgeOptions}
        >
          <Background variant="dots" gap={20} size={1} color="#334155" />
          <Controls style={{ background: '#1e293b', color: '#fff', fill: '#fff', border: '1px solid #334155' }} />
        </ReactFlow>
      </div>
      
      {/* CSS for pulse animation */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
          70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
          100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
      `}} />
    </div>
  );
}
