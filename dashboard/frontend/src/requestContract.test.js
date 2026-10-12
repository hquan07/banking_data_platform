import assert from 'node:assert/strict';
import test from 'node:test';
import { requestJson } from './requestContract.js';

test('request cancellation propagates through the shared request contract', async () => {
  const controller = new AbortController();
  const fakeFetch = (_url, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  const pending = requestJson('/slow', { signal: controller.signal }, fakeFetch);
  controller.abort();
  await assert.rejects(pending, error => error.name === 'AbortError');
});
