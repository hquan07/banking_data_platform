export const CASE_STATUSES = ['PENDING', 'INVESTIGATING', 'RESOLVED', 'IGNORED'];
export const CASE_PRIORITIES = ['P1', 'P2', 'P3', 'P4'];
export const CASE_RISK_LEVELS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

export const DISPOSITION_RESOLUTIONS = {
  CONFIRMED_FRAUD: ['FRAUD_CONFIRMED', 'REFERRED_TO_COMPLIANCE'],
  FALSE_POSITIVE: ['FALSE_POSITIVE'],
  DUPLICATE: ['DUPLICATE_CASE'],
  NO_ACTION: ['INSUFFICIENT_EVIDENCE'],
  REFERRED: ['REFERRED_TO_COMPLIANCE'],
};

const POSITIVE_INTEGER = /^[1-9]\d*$/;

export function readInvestigationLocation(search = '') {
  const params = new URLSearchParams(search);
  const pageValue = params.get('page') || '';
  const caseValue = params.get('case') || '';
  return {
    page: POSITIVE_INTEGER.test(pageValue) ? Number(pageValue) : 1,
    caseId: POSITIVE_INTEGER.test(caseValue) ? Number(caseValue) : null,
    query: (params.get('q') || '').slice(0, 100),
    status: CASE_STATUSES.includes(params.get('status')) ? params.get('status') : '',
    risk: CASE_RISK_LEVELS.includes(params.get('risk')) ? params.get('risk') : '',
  };
}

export function buildInvestigationLocation(search = '', state = {}) {
  const params = new URLSearchParams(search);
  params.set('tab', 'security');
  const values = {
    page: state.page > 1 ? String(state.page) : '',
    case: state.caseId ? String(state.caseId) : '',
    q: state.query?.trim() || '',
    status: CASE_STATUSES.includes(state.status) ? state.status : '',
    risk: CASE_RISK_LEVELS.includes(state.risk) ? state.risk : '',
  };
  Object.entries(values).forEach(([key, value]) => {
    if (value) params.set(key, value);
    else params.delete(key);
  });
  return `?${params.toString()}`;
}

export function caseSlaState(dueAt, status, now = Date.now()) {
  if (['RESOLVED', 'IGNORED'].includes(status)) return { state: 'closed', label: 'Closed' };
  if (!dueAt) return { state: 'unset', label: 'No SLA' };
  const due = new Date(dueAt).getTime();
  if (!Number.isFinite(due)) return { state: 'unset', label: 'No SLA' };
  const remainingMs = due - now;
  const absoluteHours = Math.max(1, Math.ceil(Math.abs(remainingMs) / 3_600_000));
  if (remainingMs < 0) return { state: 'overdue', label: `${absoluteHours}h overdue` };
  if (remainingMs <= 24 * 3_600_000) return { state: 'due', label: `${absoluteHours}h remaining` };
  return { state: 'on_track', label: `${Math.ceil(remainingMs / 86_400_000)}d remaining` };
}

export function isVersionConflict(status, detail = '') {
  return status === 409 || /changed|refresh|version/i.test(detail);
}

