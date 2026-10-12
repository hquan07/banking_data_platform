import assert from 'node:assert/strict';
import test from 'node:test';
import { allowedRunActions, describeRunFreshness, reconciliationLabel } from './runControlContract.js';

test('run actions follow state transitions and ADMIN authorization', () => {
  assert.deepEqual(allowedRunActions('RUNNING', 'ADMIN').map(item => item.id), ['pause', 'cancel']);
  assert.deepEqual(allowedRunActions('PAUSED', 'ADMIN').map(item => item.id), ['resume', 'cancel']);
  assert.deepEqual(allowedRunActions('COMPLETED', 'ADMIN'), []);
  assert.deepEqual(allowedRunActions('RUNNING', 'ANALYST'), []);
});

test('freshness distinguishes successful, stale, partial and failed runs', () => {
  const complete = {
    status: 'COMPLETED',
    quality: { status: 'completed', data_age_seconds: 10, sla_threshold_seconds: 30, reconciliation_checks: 2, reconciliation_completeness: 1 },
  };
  assert.equal(describeRunFreshness(complete, 0).status, 'ready');
  assert.equal(describeRunFreshness({ ...complete, quality: { ...complete.quality, data_age_seconds: 31 } }, 0).status, 'stale');
  assert.equal(describeRunFreshness({ ...complete, quality: { ...complete.quality, reconciliation_completeness: .5 } }, 0).status, 'degraded');
  assert.equal(describeRunFreshness({ ...complete, status: 'FAILED' }, 0).status, 'failed');
});

test('reconciliation copy never presents an empty result as healthy', () => {
  assert.equal(reconciliationLabel({ reconciliation_checks: 0, reconciliation_completeness: 0 }), 'Not run');
  assert.equal(reconciliationLabel({ reconciliation_checks: 4, reconciliation_completeness: .75 }), '75% · 4 checks');
});
