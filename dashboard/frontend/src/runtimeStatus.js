export const RUNTIME_STATUS_TOKENS = Object.freeze({
  ready: { label: 'Ready', tone: 'green' },
  idle: { label: 'Idle', tone: 'neutral' },
  running: { label: 'Running', tone: 'blue' },
  stale: { label: 'Stale', tone: 'amber' },
  degraded: { label: 'Degraded', tone: 'amber' },
  failed: { label: 'Failed', tone: 'red' },
  not_applicable: { label: 'Not applicable', tone: 'neutral' },
});

const LEGACY_STATUS = Object.freeze({
  active: 'running', connected: 'ready', completed: 'ready', healthy: 'ready',
  offline: 'failed', unhealthy: 'failed', partial: 'degraded',
  unknown: 'not_applicable', documented: 'not_applicable', planned: 'not_applicable',
});

const PRECEDENCE = ['failed', 'degraded', 'stale', 'running', 'ready', 'idle', 'not_applicable'];

export function normalizeRuntimeStatus(value, fallback = 'not_applicable') {
  const normalized = String(value || '').toLowerCase();
  if (RUNTIME_STATUS_TOKENS[normalized]) return normalized;
  return LEGACY_STATUS[normalized] || fallback;
}

export function selectRuntimeStatus(values) {
  const statuses = new Set((values || []).map(value => normalizeRuntimeStatus(value)));
  return PRECEDENCE.find(status => statuses.has(status)) || 'not_applicable';
}

export function formatDataAge(seconds) {
  if (seconds === null || seconds === undefined || seconds === '') return 'Not observed';
  const age = Number(seconds);
  if (!Number.isFinite(age) || age < 0) return 'Not observed';
  if (age < 60) return `${Math.round(age)}s ago`;
  if (age < 3600) return `${Math.round(age / 60)}m ago`;
  if (age < 86400) return `${Math.round(age / 3600)}h ago`;
  return `${Math.round(age / 86400)}d ago`;
}

export function humanizeRuntimeReason(value) {
  if (!value) return null;
  return String(value).replaceAll('_', ' ');
}
