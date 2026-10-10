import { test } from 'node:test';
import assert from 'node:assert/strict';
import { describeStreamStatus, parseStreamMessage } from './streamContract.js';

test('normalizes valid payment amount', () => {
  assert.deepEqual(parseStreamMessage('{"topic":"payment-events","data":{"amount":"12.50"}}'), {
    topic: 'payment-events', data: { amount: 12.5 },
  });
});

test('rejects malformed or unsupported stream messages', () => {
  for (const raw of ('bad json', '[]', '{"topic":"other","data":{}}',
    '{"topic":"payment-events","data":{"amount":"NaN"}}',
    '{"topic":"payment-events","data":{"amount":null}}')) {
    assert.equal(parseStreamMessage(raw), null);
  }
});

test('accepts source-scoped benchmark events', () => {
  assert.deepEqual(parseStreamMessage('{"topic":"benchmark-events","data":{"dataset_id":"ds1_creditcard","event_id":"ds1:1"}}'), {
    topic: 'benchmark-events', data: { dataset_id: 'ds1_creditcard', event_id: 'ds1:1' },
  });
  assert.equal(parseStreamMessage('{"topic":"benchmark-events","data":{"dataset_id":"ds1_creditcard"}}'), null);
});

test('describes live and benchmark activity without a misleading zero benchmark rate', () => {
  assert.deepEqual(describeStreamStatus({ datasetId: 'live', isConnected: true, liveRate: 0 }), {
    connection: 'Live channel connected', activity: '0 live events/s', state: 'connected',
  });
  assert.deepEqual(describeStreamStatus({ datasetId: 'ds1_creditcard', isConnected: true, now: 5000 }), {
    connection: 'Benchmark channel connected', activity: 'Replay inactive', state: 'idle',
  });
  assert.equal(describeStreamStatus({
    datasetId: 'ds1_creditcard', isConnected: true, benchmarkRate: 50, lastBenchmarkAt: 4900, now: 5000,
  }).activity, '50 benchmark events/s');
});
