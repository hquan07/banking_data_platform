import assert from 'node:assert/strict';
import test from 'node:test';
import { formatDataAge, normalizeRuntimeStatus, selectRuntimeStatus } from './runtimeStatus.js';

test('runtime status precedence surfaces the most actionable state', () => {
  assert.equal(selectRuntimeStatus(['ready', 'running', 'stale']), 'stale');
  assert.equal(selectRuntimeStatus(['idle', 'degraded', 'failed']), 'failed');
  assert.equal(selectRuntimeStatus(['not_applicable', 'ready']), 'ready');
});

test('legacy states normalize to the shared vocabulary', () => {
  assert.equal(normalizeRuntimeStatus('completed'), 'ready');
  assert.equal(normalizeRuntimeStatus('partial'), 'degraded');
  assert.equal(normalizeRuntimeStatus('offline'), 'failed');
});

test('data age formatting distinguishes missing, recent and old observations', () => {
  assert.equal(formatDataAge(null), 'Not observed');
  assert.equal(formatDataAge(12), '12s ago');
  assert.equal(formatDataAge(120), '2m ago');
  assert.equal(formatDataAge(7200), '2h ago');
});
