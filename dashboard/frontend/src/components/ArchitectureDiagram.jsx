import React, { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow, Background, Controls, MarkerType, Handle, Position,
  applyNodeChanges, BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Activity, Archive, Bell, Database, GitBranch, HardDrive,
  Monitor, Network, RefreshCw, Server, Shield, User, Zap,
} from 'lucide-react';
import { ARCHITECTURE_VIEWS, topologyForView } from '../architectureContract';

const icons = {
  activity: Activity, archive: Archive, bell: Bell, database: Database,
  graph: GitBranch, storage: HardDrive, monitor: Monitor, network: Network,
  retry: RefreshCw, server: Server, shield: Shield, user: User, zap: Zap,
};

const statusColors = {
  healthy: '#22c55e', unhealthy: '#ef4444', documented: '#64748b', planned: '#f59e0b',
  inactive: '#f59e0b', ondemand: '#60a5fa',
};

const statusLabels = {
  healthy: 'Sẵn sàng theo API readiness',
  unhealthy: 'Không phản hồi hoặc probe thất bại',
  documented: 'Đã triển khai, chưa có direct health probe',
  planned: 'Chưa tích hợp',
  inactive: 'Container có mặt nhưng data flow chưa cấu hình',
  ondemand: 'Chỉ chạy khi operator chủ động kích hoạt',
};

const handlePositions = [
  ['top', Position.Top], ['right', Position.Right],
  ['bottom', Position.Bottom], ['left', Position.Left],
];

function ArchitectureNode({ data, selected }) {
  const Icon = icons[data.icon] || Server;
  const status = data.health || data.status || 'documented';
  const color = status === 'unhealthy' ? statusColors.unhealthy : data.color;
  const dashed = ['planned', 'inactive', 'ondemand'].includes(status);

  return <div style={{
    width: 208, padding: '12px 14px', position: 'relative', cursor: 'pointer',
    borderRadius: 12, color: '#f8fafc', background: 'rgba(30, 41, 59, 0.96)',
    border: `2px ${dashed ? 'dashed' : 'solid'} ${color}`,
    boxShadow: selected ? `0 0 0 3px ${color}55, 0 12px 28px #0008` : '0 5px 16px #0005',
  }}>
    {handlePositions.map(([name, position]) => <React.Fragment key={name}>
      <Handle id={`target-${name}`} type="target" position={position} style={{ width: 7, height: 7, opacity: 0, border: 0 }} />
      <Handle id={`source-${name}`} type="source" position={position} style={{ width: 7, height: 7, background: '#64748b', border: '1px solid #0b0f19' }} />
    </React.Fragment>)}
    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
      <span style={{ display: 'flex', padding: 8, borderRadius: 8, background: '#ffffff17' }}>
        <Icon size={20} color={color} aria-hidden="true" />
      </span>
      <span style={{ minWidth: 0 }}>
        <strong style={{ display: 'block', fontSize: 13, lineHeight: 1.25 }}>{data.label}</strong>
        <small style={{ display: 'block', color: '#cbd5e1', fontSize: 11, marginTop: 3 }}>{data.sublabel}</small>
      </span>
    </div>
    <span title={statusLabels[status]} aria-label={statusLabels[status]} style={{
      position: 'absolute', top: -7, right: -7, width: 15, height: 15,
      borderRadius: '50%', background: statusColors[status], border: '2px solid #0b0f19',
      boxShadow: status === 'healthy' ? `0 0 9px ${statusColors.healthy}` : 'none',
    }} />
    {selected && <div style={{
      position: 'absolute', zIndex: 20, top: 'calc(100% + 10px)', left: 0,
      width: 250, padding: 12, borderRadius: 9, background: '#0f172af5',
      border: '1px solid #475569', boxShadow: '0 12px 28px #000a',
      fontSize: 12, lineHeight: 1.45, color: '#cbd5e1',
    }}>
      <div>{data.description}</div>
      <div style={{ color: statusColors[status], fontWeight: 700, marginTop: 7 }}>{statusLabels[status]}</div>
    </div>}
  </div>;
}

const nodeTypes = { architecture: ArchitectureNode };
const probedNodes = {
  backend: 'api', postgres: 'postgres', kafka: 'kafka', redis: 'redis',
  neo4j: 'neo4j', clickhouse: 'clickhouse', minio: 'minio',
};

const viewDescriptions = {
  realtime: 'Event topics, processors, stream gateway và operational stores.',
  batch: 'Customer Silver, fail-closed DQ và Gold warehouse path.',
  serving: 'Dashboard APIs, data stores, monitoring và integration chưa cấu hình.',
  all: 'Toàn bộ topology; dùng các view chuyên biệt khi cần đọc rõ từng đường nối.',
};

function nodesForView(viewId) {
  return topologyForView(viewId).nodes.map(item => ({
    id: item.id, type: 'architecture', position: item.position, data: item,
  }));
}

function automaticSides(edge, nodeById) {
  if (edge.sourceSide && edge.targetSide) return [edge.sourceSide, edge.targetSide];
  const source = nodeById.get(edge.source)?.position;
  const target = nodeById.get(edge.target)?.position;
  if (!source || !target) return ['bottom', 'top'];
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? ['right', 'left'] : ['left', 'right'];
  return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom'];
}

function edgesForView(viewId, nodes) {
  const nodeById = new Map(nodes.map(item => [item.id, item]));
  return topologyForView(viewId).edges.map(item => {
    const [sourceSide, targetSide] = automaticSides(item, nodeById);
    return {
      id: item.id, source: item.source, target: item.target, label: item.label,
      sourceHandle: `source-${sourceSide}`, targetHandle: `target-${targetSide}`,
      type: 'smoothstep', animated: false, pathOptions: { borderRadius: 14, offset: 24 },
      style: {
        stroke: item.color, strokeWidth: 2,
        ...(item.state !== 'configured' ? { strokeDasharray: '6 5' } : {}),
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: item.color },
      labelStyle: { fill: '#f8fafc', fontWeight: 600, fontSize: 11 },
      labelBgStyle: { fill: '#1e293b', fillOpacity: 0.95 },
      data: { state: item.state },
    };
  });
}

export default function ArchitectureDiagram({ health = {}, lastChecked = null }) {
  const [viewId, setViewId] = useState('realtime');
  const [nodes, setNodes] = useState(() => nodesForView('realtime'));
  const onNodesChange = useCallback(changes => setNodes(current => applyNodeChanges(changes, current)), []);
  const selectView = nextView => {
    setViewId(nextView);
    setNodes(nodesForView(nextView));
  };
  const edges = useMemo(() => edgesForView(viewId, nodes), [nodes, viewId]);
  const visibleNodes = useMemo(() => nodes.map(item => {
    const probe = probedNodes[item.id];
    if (!probe) return item;
    const value = health[probe];
    const status = typeof value === 'boolean' ? (value ? 'healthy' : 'unhealthy') : item.data.status;
    return { ...item, data: { ...item.data, health: status } };
  }), [health, nodes]);

  return <>
    <div className="architecture-view-switcher" role="group" aria-label="Architecture layer">
      {ARCHITECTURE_VIEWS.map(view => <button
        type="button" key={view.id} aria-pressed={viewId === view.id}
        className={viewId === view.id ? 'active' : ''} onClick={() => selectView(view.id)}
      >{view.label}</button>)}
      <span>{viewDescriptions[viewId]}</span>
    </div>
    <div className="architecture-legend">
      <span><i style={{ background: statusColors.healthy }} /> Sẵn sàng (API readiness)</span>
      <span><i style={{ background: statusColors.unhealthy }} /> Probe thất bại</span>
      <span><i style={{ background: statusColors.documented }} /> Đã triển khai, chưa probe</span>
      <span><i style={{ background: statusColors.planned }} /> Chưa tích hợp</span>
      <span><i className="legend-diamond" style={{ borderColor: statusColors.inactive }} /> Service có mặt, flow chưa cấu hình</span>
      <span><i className="legend-diamond" style={{ borderColor: statusColors.ondemand }} /> On-demand</span>
      {lastChecked && <span>Kiểm tra lúc {lastChecked.toLocaleTimeString('vi-VN')}</span>}
    </div>
    <p className="architecture-contract-note">Đường nối thể hiện integration contract trong code; không khẳng định event đang chảy tại thời điểm xem. Nét đứt là on-demand hoặc chưa cấu hình.</p>
    <div className="architecture-flow" style={{ height: viewId === 'all' ? 900 : 680 }}>
      <ReactFlow
        key={viewId} colorMode="dark" nodes={visibleNodes} edges={edges} nodeTypes={nodeTypes}
        onNodesChange={onNodesChange} nodesConnectable={false} edgesFocusable={false}
        fitView fitViewOptions={{ padding: 0.18 }} attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  </>;
}
