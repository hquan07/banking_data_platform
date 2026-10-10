/**
 * @typedef {{ topic: 'payment-events'|'benchmark-events'|'fraud-events'|'aml-events', data: Record<string, unknown> }} StreamMessage
 */

/** @param {string} raw @returns {StreamMessage|null} */
export function parseStreamMessage(raw) {
  let message;
  try {
    message = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!message || typeof message !== 'object' || Array.isArray(message)) return null;
  if (!['payment-events', 'benchmark-events', 'fraud-events', 'aml-events'].includes(message.topic)) return null;
  if (!message.data || typeof message.data !== 'object' || Array.isArray(message.data)) return null;
  if (message.topic === 'payment-events') {
    const rawAmount = message.data.amount;
    if ((typeof rawAmount !== 'number' && typeof rawAmount !== 'string') || rawAmount === '') return null;
    const amount = Number(rawAmount);
    if (!Number.isFinite(amount) || amount <= 0) return null;
    return { topic: message.topic, data: { ...message.data, amount } };
  }
  if (message.topic === 'benchmark-events') {
    if (typeof message.data.dataset_id !== 'string' || !message.data.dataset_id) return null;
    if (typeof message.data.event_id !== 'string' || !message.data.event_id) return null;
  }
  return message;
}

export function describeStreamStatus({ datasetId, isConnected, liveRate = 0, benchmarkRate = 0, lastBenchmarkAt = 0, now = Date.now() }) {
  const isBenchmark = datasetId !== 'live';
  if (!isConnected) {
    return {
      connection: 'Stream channel offline',
      activity: isBenchmark ? 'Replay unavailable' : '0 live events/s',
      state: 'offline',
    };
  }
  if (!isBenchmark) {
    return { connection: 'Live channel connected', activity: `${liveRate} live events/s`, state: 'connected' };
  }
  const replayActive = lastBenchmarkAt > 0 && now - lastBenchmarkAt < 2500;
  return {
    connection: 'Benchmark channel connected',
    activity: benchmarkRate > 0 ? `${benchmarkRate} benchmark events/s` : replayActive ? 'Replay active · waiting' : 'Replay inactive',
    state: replayActive ? 'active' : 'idle',
  };
}
