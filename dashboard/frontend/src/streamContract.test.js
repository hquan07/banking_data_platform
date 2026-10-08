import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseStreamMessage } from './streamContract.js';

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
