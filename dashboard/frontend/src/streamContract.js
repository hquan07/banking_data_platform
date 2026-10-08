/**
 * @typedef {{ topic: 'payment-events'|'fraud-events'|'aml-events', data: Record<string, unknown> }} StreamMessage
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
  if (!['payment-events', 'fraud-events', 'aml-events'].includes(message.topic)) return null;
  if (!message.data || typeof message.data !== 'object' || Array.isArray(message.data)) return null;
  if (message.topic === 'payment-events') {
    const rawAmount = message.data.amount;
    if ((typeof rawAmount !== 'number' && typeof rawAmount !== 'string') || rawAmount === '') return null;
    const amount = Number(rawAmount);
    if (!Number.isFinite(amount) || amount <= 0) return null;
    return { topic: message.topic, data: { ...message.data, amount } };
  }
  return message;
}
