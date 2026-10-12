import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Pause, Play, RefreshCw, XCircle } from 'lucide-react';
import { AuthContext } from './AuthContext';
import { DATASET_DEFINITIONS } from './DatasetContext';
import { Badge, formatNumber, Panel, RuntimeStatus, StateMessage } from './ui';
import {
  RUN_STATUS_TONES, allowedRunActions, describeRunFreshness, reconciliationLabel,
} from '../runControlContract';

const RUN_STATES = ['CREATED', 'RUNNING', 'PAUSING', 'PAUSED', 'CANCELLING', 'CANCELLED', 'COMPLETED', 'FAILED'];
const ACTION_ICONS = { pause: Pause, resume: Play, cancel: XCircle };

function apiBase() { return window._env_?.API_URL || 'http://localhost:8000'; }
function compactId(value) { return value ? `${value.slice(0, 8)}…${value.slice(-4)}` : '—'; }
function displayDate(value) { return value ? new Date(value).toLocaleString('vi-VN') : '—'; }
function ProgressCell({ progress }) {
  const percent = progress?.percent;
  if (percent === null || percent === undefined) return <span className="run-muted">No offset window</span>;
  return <div className="run-progress" aria-label={`${percent}% complete, lag ${progress.lag}`}>
    <div><span style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} /></div>
    <small>{formatNumber(progress.processed)} / {formatNumber(progress.total)} · lag {formatNumber(progress.lag)}</small>
  </div>;
}

export default function DataRunsSection() {
  const { token, user } = useContext(AuthContext);
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [datasetFilter, setDatasetFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionId, setActionId] = useState(null);
  const [notice, setNotice] = useState('');
  const listController = useRef(null);
  const detailController = useRef(null);

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const loadRuns = useCallback(async ({ quiet = false } = {}) => {
    if (!token) return;
    listController.current?.abort();
    const controller = new AbortController();
    listController.current = controller;
    if (!quiet) setLoading(true);
    setError('');
    const query = new URLSearchParams({ limit: '20', page: String(page) });
    if (statusFilter) query.set('status', statusFilter);
    if (datasetFilter) query.set('dataset_id', datasetFilter);
    try {
      const response = await fetch(`${apiBase()}/api/runs?${query}`, { headers, signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setRuns(payload.data || []);
      setTotal(payload.total || 0);
    } catch (fetchError) {
      if (fetchError.name !== 'AbortError') setError(`Không thể tải Data Runs: ${fetchError.message}`);
    } finally {
      if (!quiet && !controller.signal.aborted) setLoading(false);
    }
  }, [datasetFilter, headers, page, statusFilter, token]);

  const loadDetail = useCallback(async runId => {
    if (!runId) return;
    detailController.current?.abort();
    const controller = new AbortController();
    detailController.current = controller;
    setDetailLoading(true); setDetail(null); setError('');
    try {
      const response = await fetch(`${apiBase()}/api/runs/${runId}`, { headers, signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setDetail(await response.json());
    } catch (fetchError) {
      if (fetchError.name !== 'AbortError') setError(`Không thể tải run detail: ${fetchError.message}`);
    } finally { if (!controller.signal.aborted) setDetailLoading(false); }
  }, [headers]);

  useEffect(() => {
    loadRuns();
    const interval = window.setInterval(() => loadRuns({ quiet: true }), 15000);
    return () => { window.clearInterval(interval); listController.current?.abort(); detailController.current?.abort(); };
  }, [loadRuns]);

  const toggleDetail = runId => {
    if (selectedId === runId) { setSelectedId(null); setDetail(null); return; }
    setSelectedId(runId); loadDetail(runId);
  };

  const transition = async (run, action) => {
    if (action.destructive && !window.confirm(`Cancel run ${run.run_id}? The producer will stop at its next control checkpoint and this cannot be resumed.`)) return;
    setActionId(`${run.run_id}:${action.id}`); setError(''); setNotice('');
    try {
      const response = await fetch(`${apiBase()}/api/runs/${run.run_id}/transition`, {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: action.targetStatus, version: run.version }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP ${response.status}`);
      }
      const changed = await response.json();
      setRuns(previous => previous.map(item => item.run_id === run.run_id ? { ...item, ...changed } : item));
      setNotice(`${action.label} request accepted for ${compactId(run.run_id)}.`);
      if (selectedId === run.run_id) await loadDetail(run.run_id);
      await loadRuns({ quiet: true });
    } catch (transitionError) {
      setError(`Không thể ${action.label.toLowerCase()} run: ${transitionError.message}`);
    } finally { setActionId(null); }
  };

  return <Panel className="col-span-12 data-runs-panel" title="Data Runs" subtitle="Durable replay state, offsets, freshness và reconciliation theo từng run" action={<button className="secondary-button" onClick={() => loadRuns()} disabled={loading} aria-label="Refresh data runs"><RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh</button>}>
    <div className="run-toolbar">
      <label>Status<select value={statusFilter} onChange={event => { setStatusFilter(event.target.value); setPage(1); }}><option value="">All states</option>{RUN_STATES.map(state => <option key={state}>{state}</option>)}</select></label>
      <label>Dataset<select value={datasetFilter} onChange={event => { setDatasetFilter(event.target.value); setPage(1); }}><option value="">All datasets</option>{Object.entries(DATASET_DEFINITIONS).map(([id, definition]) => <option value={id} key={id}>{definition.shortLabel || definition.label}</option>)}</select></label>
      <span>{total ? `${formatNumber((page - 1) * 20 + 1)}–${formatNumber(Math.min(page * 20, total))} of ` : ''}{formatNumber(total)} runs</span>
      {user?.role !== 'ADMIN' && <span className="run-readonly-note">Read-only · ADMIN required for run control</span>}
    </div>
    {notice && <div className="inline-message success" role="status">{notice}</div>}
    {error && <StateMessage type="error">{error}</StateMessage>}
    {loading && !runs.length ? <StateMessage type="loading">Đang tải run ledger…</StateMessage> : !error && !runs.length ? <StateMessage>Chưa có run phù hợp bộ lọc. Empty không được xem là healthy.</StateMessage> : runs.length > 0 && <><div className="dataset-table-wrap data-runs-scroll"><table className="data-runs-table"><thead><tr><th>Run / state</th><th>Owner / source</th><th>Dataset version</th><th>Progress / lag</th><th>Rate</th><th>Freshness</th><th>Reconciliation</th><th>Updated</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{runs.map(run => {
      const freshness = describeRunFreshness(run);
      const actions = allowedRunActions(run.status, user?.role);
      const expanded = selectedId === run.run_id;
      return <React.Fragment key={run.run_id}><tr className={expanded ? 'run-row-selected' : ''}>
        <td><button className="run-id-button" onClick={() => toggleDetail(run.run_id)} aria-expanded={expanded} aria-controls={`run-detail-${run.run_id}`}><span>{compactId(run.run_id)}</span>{expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button><Badge tone={RUN_STATUS_TONES[run.status] || 'neutral'}>{run.status}</Badge></td>
        <td><strong>{run.owner_username || `User #${run.owner_user_id}`}</strong><small>{run.source_kind?.replaceAll('_', ' ')}</small></td>
        <td><strong>{DATASET_DEFINITIONS[run.dataset_id]?.shortLabel || run.dataset_id}</strong><small>{run.dataset_version}</small></td>
        <td><ProgressCell progress={run.progress} /></td>
        <td><strong>{formatNumber(run.requested_rate, 2)}</strong><small>events/s</small></td>
        <td><RuntimeStatus status={freshness.status} ageSeconds={run.quality?.data_age_seconds} lastSuccessAt={run.quality?.last_success_at} reason={freshness.reason || run.quality?.reason} detail={`${formatNumber(run.requested_rate, 2)} events/s`} /></td>
        <td><strong>{reconciliationLabel(run.quality)}</strong><small>{run.quality?.reason?.replaceAll('_', ' ') || 'No discrepancy'}</small></td>
        <td>{displayDate(run.updated_at)}</td>
        <td><div className="run-actions">{actions.map(action => {
          const Icon = ACTION_ICONS[action.id]; const busy = actionId === `${run.run_id}:${action.id}`;
          return <button key={action.id} className={`run-action-button ${action.destructive ? 'danger-button' : ''}`} onClick={() => transition(run, action)} disabled={Boolean(actionId)} aria-label={`${action.label} run ${compactId(run.run_id)}`} title={action.label}>{busy ? <RefreshCw className="spin" size={14} /> : <Icon size={14} />}</button>;
        })}</div></td>
      </tr>{expanded && <tr className="run-detail-row"><td colSpan="9" id={`run-detail-${run.run_id}`}>{detailLoading ? <StateMessage type="loading">Đang tải chi tiết run…</StateMessage> : detail ? <RunDetail detail={detail} /> : null}</td></tr>}</React.Fragment>;
    })}</tbody></table></div>{total > 20 && <div className="pagination run-pagination"><span>Page {page} of {Math.ceil(total / 20)}</span><div><button onClick={() => setPage(value => Math.max(1, value - 1))} disabled={page === 1 || loading}>Previous</button><button onClick={() => setPage(value => Math.min(Math.ceil(total / 20), value + 1))} disabled={page >= Math.ceil(total / 20) || loading}>Next</button></div></div>}</>}
  </Panel>;
}

function RunDetail({ detail }) {
  const counters = detail.counters || [];
  const reconciliations = detail.reconciliation || [];
  const freshness = describeRunFreshness(detail);
  return <div className="run-detail" aria-label={`Run detail ${detail.run_id}`}>
    <div className="run-detail-summary">
      <div><span>Operational status</span><RuntimeStatus status={freshness.status} ageSeconds={detail.quality?.data_age_seconds} lastSuccessAt={detail.quality?.last_success_at} reason={freshness.reason || detail.quality?.reason} detail={`${formatNumber(detail.requested_rate, 2)} events/s`} /></div>
      <div><span>Run ID</span><strong>{detail.run_id}</strong></div>
      <div><span>Contract / evaluator</span><strong>v{detail.contract_version} · {detail.evaluator_version}</strong></div>
      <div><span>Offset window</span><strong>{detail.requested_start_offset ?? '—'} → {detail.requested_end_offset ?? 'open'}</strong></div>
      <div><span>Terminal reason</span><strong>{detail.failure_reason || (['FAILED', 'CANCELLED'].includes(detail.status) ? 'No reason recorded' : 'Not terminal')}</strong></div>
    </div>
    <div className="run-detail-grid">
      <section><h3>Offsets</h3>{detail.offsets?.length ? <table><thead><tr><th>Topic / partition</th><th>Start</th><th>Current</th><th>End</th><th>Lag</th></tr></thead><tbody>{detail.offsets.map(offset => <tr key={`${offset.topic}:${offset.partition}`}><td>{offset.topic} / {offset.partition}</td><td>{formatNumber(offset.start_offset)}</td><td>{formatNumber(offset.current_offset)}</td><td>{formatNumber(offset.end_offset)}</td><td>{offset.end_offset === null ? '—' : formatNumber(Math.max(0, offset.end_offset - (offset.current_offset ?? offset.start_offset)))}</td></tr>)}</tbody></table> : <StateMessage>No durable offset window.</StateMessage>}</section>
      <section><h3>Count flow</h3>{counters.length ? <div className="run-counter-grid">{counters.map(counter => <div key={counter.counter_name}><span>{counter.counter_name.replaceAll('_', ' ')}</span><strong>{formatNumber(counter.counter_value)}</strong></div>)}</div> : <StateMessage>No counters recorded.</StateMessage>}</section>
    </div>
    <section className="run-reconciliation"><h3>Reconciliation evidence</h3>{reconciliations.length ? <div className="dataset-table-wrap"><table><thead><tr><th>Store / metric</th><th>Class</th><th>Expected</th><th>Actual</th><th>Delta</th><th>Bounded samples</th></tr></thead><tbody>{reconciliations.map(row => <tr key={`${row.check_id}:${row.classification}`}><td><strong>{row.store}</strong><small>{row.metric}</small></td><td><Badge tone={['EXACT', 'QUARANTINED'].includes(row.classification) ? 'green' : row.classification === 'PENDING' ? 'amber' : 'red'}>{row.classification}</Badge></td><td>{formatNumber(row.expected_count)}</td><td>{formatNumber(row.actual_count)}</td><td>{formatNumber(row.discrepancy_count)}</td><td><code>{row.sample_ids?.length ? row.sample_ids.join(', ') : '—'}</code></td></tr>)}</tbody></table></div> : <StateMessage>Reconciliation has not run; health is unknown.</StateMessage>}</section>
  </div>;
}
