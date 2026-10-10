import assert from 'node:assert/strict';
import test from 'node:test';
import {
  ARCHITECTURE_EDGES, ARCHITECTURE_LAYOUTS, ARCHITECTURE_NODES, topologyForView,
} from './architectureContract.js';

const edgeKeys = new Set(ARCHITECTURE_EDGES.map(edge => `${edge.source}->${edge.target}`));

test('architecture topology has unique nodes, edges and valid endpoints', () => {
  const nodeIds = new Set(ARCHITECTURE_NODES.map(node => node.id));
  assert.equal(nodeIds.size, ARCHITECTURE_NODES.length);
  assert.equal(edgeKeys.size, ARCHITECTURE_EDGES.length);
  for (const edge of ARCHITECTURE_EDGES) {
    assert.ok(nodeIds.has(edge.source), `unknown source: ${edge.source}`);
    assert.ok(nodeIds.has(edge.target), `unknown target: ${edge.target}`);
  }
  for (const [viewId, layout] of Object.entries(ARCHITECTURE_LAYOUTS)) {
    assert.ok(Object.keys(layout).every(nodeId => nodeIds.has(nodeId)), `unknown node in ${viewId}`);
    const topology = topologyForView(viewId);
    assert.ok(topology.nodes.length > 0);
    assert.ok(topology.edges.every(edge => layout[edge.source] && layout[edge.target]));
  }
});

test('architecture topology preserves required deployed data flows', () => {
  const requiredEdges = [
    'kafka->backend', 'kafka->retry', 'retry->kafka',
    'fraud-engine->kafka', 'benchmark-processor->kafka', 'benchmark-graph-processor->kafka',
    'backend->redis', 'postgres->batch-dq', 'batch-dq->minio', 'minio->batch-dq',
    'batch-dq->postgres', 'batch-dq->clickhouse', 'kafka->kafka-exporter',
    'kafka-exporter->prometheus', 'backend->prometheus', 'prometheus->grafana',
  ];
  for (const required of requiredEdges) assert.ok(edgeKeys.has(required), `missing ${required}`);
});

test('unconfigured integrations cannot appear as active flows', () => {
  const nodes = Object.fromEntries(ARCHITECTURE_NODES.map(node => [node.id, node]));
  assert.equal(nodes['transfer-source'].status, 'planned');
  assert.equal(nodes.debezium.status, 'inactive');
  assert.equal(nodes.superset.status, 'inactive');
  const liveSourceEdge = ARCHITECTURE_EDGES.find(item => `${item.source}->${item.target}` === 'transfer-source->kafka');
  assert.equal(liveSourceEdge.state, 'planned');
  assert.match(liveSourceEdge.label, /chưa cấu hình/);
  for (const key of ['postgres->debezium', 'debezium->kafka', 'postgres->superset', 'clickhouse->superset']) {
    const edge = ARCHITECTURE_EDGES.find(item => `${item.source}->${item.target}` === key);
    assert.equal(edge.state, 'inactive');
  }
});
