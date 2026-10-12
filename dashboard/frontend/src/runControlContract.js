export const RUN_STATUS_TONES = Object.freeze({
  CREATED: 'neutral', RUNNING: 'blue', PAUSING: 'amber', PAUSED: 'amber',
  CANCELLING: 'amber', CANCELLED: 'neutral', COMPLETED: 'green', FAILED: 'red',
});

const ACTIONS_BY_STATUS = Object.freeze({
  RUNNING: [
    { id: 'pause', label: 'Pause', targetStatus: 'PAUSING' },
    { id: 'cancel', label: 'Cancel', targetStatus: 'CANCELLING', destructive: true },
  ],
  PAUSING: [
    { id: 'cancel', label: 'Cancel', targetStatus: 'CANCELLING', destructive: true },
  ],
  PAUSED: [
    { id: 'resume', label: 'Resume', targetStatus: 'RUNNING' },
    { id: 'cancel', label: 'Cancel', targetStatus: 'CANCELLING', destructive: true },
  ],
});

export function allowedRunActions(status, role) {
  if (role !== 'ADMIN') return [];
  return ACTIONS_BY_STATUS[status] || [];
}

export function describeRunFreshness(run) {
  const quality = run?.quality || {};
  const completeness = Number(quality.reconciliation_completeness);
  const checks = Number(quality.reconciliation_checks || 0);
  const age = Number(quality.data_age_seconds);
  const threshold = Number(quality.sla_threshold_seconds);

  if (run?.status === 'FAILED' || quality.status === 'failed') {
    return { status: 'failed', label: 'Failed', tone: 'red' };
  }
  if (quality.status === 'degraded') {
    return { status: 'degraded', label: 'Degraded', tone: 'red' };
  }
  if (checks > 0 && Number.isFinite(completeness) && completeness < 1) {
    return { status: 'degraded', label: 'Degraded', tone: 'amber', reason: 'reconciliation_incomplete' };
  }
  if (Number.isFinite(age) && Number.isFinite(threshold) && threshold >= 0 && age > threshold) {
    return { status: 'stale', label: 'Stale', tone: 'amber' };
  }
  if (run?.status === 'COMPLETED' && quality.status === 'completed') {
    return { status: 'ready', label: 'Ready', tone: 'green' };
  }
  if (quality.status === 'running') {
    return { status: 'running', label: 'Active', tone: 'blue' };
  }
  return { status: quality.status || 'not_applicable', label: quality.status === 'idle' ? 'Idle' : 'Not applicable', tone: 'neutral' };
}

export function reconciliationLabel(quality) {
  const checks = Number(quality?.reconciliation_checks || 0);
  if (!checks) return 'Not run';
  const completeness = Math.max(0, Math.min(1, Number(quality?.reconciliation_completeness || 0)));
  return `${Math.round(completeness * 100)}% · ${checks} checks`;
}
