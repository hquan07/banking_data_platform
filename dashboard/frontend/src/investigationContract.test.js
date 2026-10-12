import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildInvestigationLocation,
  caseSlaState,
  isVersionConflict,
  readInvestigationLocation,
} from './investigationContract.js';

test('investigation location validates and preserves stable queue state', () => {
  assert.deepEqual(
    readInvestigationLocation('?tab=security&page=3&case=42&q=velocity&status=PENDING&risk=HIGH'),
    { page: 3, caseId: 42, query: 'velocity', status: 'PENDING', risk: 'HIGH' },
  );
  assert.deepEqual(
    readInvestigationLocation('?page=-1&case=none&status=UNKNOWN&risk=UNKNOWN'),
    { page: 1, caseId: null, query: '', status: '', risk: '' },
  );
});

test('investigation location removes default values without losing unrelated context', () => {
  const next = buildInvestigationLocation('?tab=security&account=A-1&page=9', {
    page: 1, caseId: 17, query: '', status: 'INVESTIGATING', risk: '',
  });
  const params = new URLSearchParams(next);
  assert.equal(params.get('tab'), 'security');
  assert.equal(params.get('account'), 'A-1');
  assert.equal(params.get('case'), '17');
  assert.equal(params.get('status'), 'INVESTIGATING');
  assert.equal(params.has('page'), false);
});

test('case SLA distinguishes overdue, near due, on-track and closed cases', () => {
  const now = Date.parse('2026-10-12T00:00:00Z');
  assert.equal(caseSlaState('2026-10-11T20:00:00Z', 'PENDING', now).state, 'overdue');
  assert.equal(caseSlaState('2026-10-12T12:00:00Z', 'PENDING', now).state, 'due');
  assert.equal(caseSlaState('2026-10-15T00:00:00Z', 'INVESTIGATING', now).state, 'on_track');
  assert.equal(caseSlaState('2026-10-11T20:00:00Z', 'RESOLVED', now).state, 'closed');
});

test('version conflicts are recognized from status and backend detail', () => {
  assert.equal(isVersionConflict(409, ''), true);
  assert.equal(isVersionConflict(422, 'Case changed; refresh before updating'), true);
  assert.equal(isVersionConflict(422, 'Unsupported priority'), false);
});
