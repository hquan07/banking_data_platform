import assert from 'node:assert/strict';
import test from 'node:test';
import {
  allowedModesForDataset, BOOTSTRAP_CAPABILITY_MANIFEST, canShowGroundTruth,
  fixedDatasetForTab, normalizeDashboardContext, tabCapability, validateCapabilityManifest,
} from './datasetContextContract.js';

test('normalizes live sources to operational mode', () => {
  assert.deepEqual(normalizeDashboardContext({ datasetId: 'live', mode: 'benchmark' }), {
    datasetId: 'live', mode: 'operational',
  });
  assert.deepEqual(allowedModesForDataset('live'), ['operational']);
  assert.equal(canShowGroundTruth({ datasetId: 'live', mode: 'benchmark' }), false);
});

test('normalizes public datasets to benchmark mode', () => {
  for (const datasetId of ['ds1_creditcard', 'ds3_paysim', 'ds4_baf']) {
    assert.deepEqual(normalizeDashboardContext({ datasetId, mode: 'operational' }), {
      datasetId, mode: 'benchmark',
    });
    assert.equal(canShowGroundTruth({ datasetId, mode: 'operational' }), true);
  }
});

test('rejects unknown persisted context values', () => {
  assert.deepEqual(normalizeDashboardContext({ datasetId: 'unknown', mode: 'benchmark' }), {
    datasetId: 'live', mode: 'operational',
  });
  assert.deepEqual(normalizeDashboardContext(null), {
    datasetId: 'live', mode: 'operational',
  });
});

test('locks investigations and AML Network to DS3 PaySim', () => {
  assert.equal(fixedDatasetForTab('security'), 'ds3_paysim');
  assert.equal(fixedDatasetForTab('analytics'), 'ds3_paysim');
  assert.equal(fixedDatasetForTab('overview'), null);
});

test('navigation uses manifest semantics and runtime availability', () => {
  const manifest = structuredClone(BOOTSTRAP_CAPABILITY_MANIFEST);
  const ds3 = manifest.datasets.find(item => item.dataset_id === 'ds3_paysim');
  ds3.tab_availability.analytics.available = false;
  ds3.tab_availability.analytics.reason = 'Unavailable dependencies: neo4j';
  assert.equal(fixedDatasetForTab('analytics', manifest), 'ds3_paysim');
  assert.deepEqual(tabCapability('ds3_paysim', 'analytics', manifest), {
    supported: true,
    available: false,
    required_dependencies: [],
    missing_dependencies: [],
    reason: 'Unavailable dependencies: neo4j',
  });
  assert.equal(tabCapability('live', 'history', manifest).supported, false);
});

test('rejects unsupported or incomplete manifests before data tabs render', () => {
  assert.throws(() => validateCapabilityManifest({ manifest_version: 2, datasets: [] }), /Unsupported/);
  assert.throws(() => validateCapabilityManifest({ manifest_version: 1, datasets: [] }), /missing/);
  assert.equal(validateCapabilityManifest(BOOTSTRAP_CAPABILITY_MANIFEST).manifest_version, 1);
});
