import assert from 'node:assert/strict';
import test from 'node:test';
import {
  allowedModesForDataset, canShowGroundTruth, normalizeDashboardContext,
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
