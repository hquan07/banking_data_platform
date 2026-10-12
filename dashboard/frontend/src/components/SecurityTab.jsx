import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, Clock3, Download, ExternalLink, FileCheck2,
  MessageSquarePlus, Network, RefreshCw, Save, Search, ShieldAlert, Upload,
  UserRoundCheck,
} from 'lucide-react';
import { AuthContext } from './AuthContext';
import { useDatasetContext } from './DatasetContext';
import {
  buildInvestigationLocation, caseSlaState, CASE_PRIORITIES, CASE_RISK_LEVELS,
  CASE_STATUSES, DISPOSITION_RESOLUTIONS, isVersionConflict, readInvestigationLocation,
} from '../investigationContract';
import { Badge, formatNumber, MetricCard, PageHeader, Panel, StateMessage } from './ui';

const PAGE_SIZE = 12;
const STATUS_TONE = { PENDING: 'amber', INVESTIGATING: 'blue', RESOLVED: 'green', IGNORED: 'neutral' };
const PRIORITY_TONE = { P1: 'red', P2: 'amber', P3: 'blue', P4: 'neutral' };
const DISPOSITION_LABELS = {
  CONFIRMED_FRAUD: 'Confirmed fraud', FALSE_POSITIVE: 'False positive',
  DUPLICATE: 'Duplicate', NO_ACTION: 'No action', REFERRED: 'Refer to compliance',
};

function apiBase() { return window._env_?.API_URL || 'http://localhost:8000'; }
function formatDate(value) { return value ? new Date(value).toLocaleString('vi-VN') : '—'; }
function toDateTimeInput(value) {
  if (!value) return '';
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

async function requestJson(path, token, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

async function sha256(file) {
  const digest = await window.crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function openWorkspace(tab, context = {}) {
  const params = new URLSearchParams();
  params.set('tab', tab);
  Object.entries(context).forEach(([key, value]) => { if (value) params.set(key, String(value)); });
  window.history.pushState({}, '', `${window.location.pathname}?${params.toString()}`);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

function SourceEvidence({ item, source, loading }) {
  const sourceEventIds = item.source_event_ids?.length ? item.source_event_ids : item.event_id ? [item.event_id] : [];
  if (!sourceEventIds.length) return <StateMessage>Case này chưa liên kết source event.</StateMessage>;
  return <div className="source-evidence">
    <div className="source-evidence-heading"><div><span className="detail-label">Benchmark source events</span><strong>{sourceEventIds.join(' · ')}</strong></div><Badge tone="amber">{item.dataset_id || 'unknown'}</Badge></div>
    {loading ? <StateMessage type="loading">Đang tải source evidence…</StateMessage> : source ? <>
      <dl className="case-data-grid">
        <div><dt>Source row</dt><dd>{source.source_row_id}</dd></div>
        <div><dt>Event type</dt><dd>{source.event_type}</dd></div>
        <div><dt>Relative time</dt><dd>{source.relative_time_value} {source.relative_time_unit}</dd></div>
        <div><dt>Ground truth</dt><dd>{source.ground_truth_is_fraud ? 'Fraud' : 'Normal'}</dd></div>
        <div><dt>Model decision</dt><dd>{source.evaluation ? source.evaluation.predicted_fraud ? 'Predicted fraud' : 'Predicted normal' : 'Not evaluated'}</dd></div>
        <div><dt>Source file</dt><dd>{source.source_file}</dd></div>
      </dl>
      <details className="source-payload"><summary>Source payload</summary><pre>{JSON.stringify(source.payload, null, 2)}</pre></details>
    </> : <StateMessage type="error">Không tìm thấy source event cho run của case.</StateMessage>}
    <button className="secondary-button" onClick={() => openWorkspace('analytics', { account: item.account_id, event: sourceEventIds[0], run: item.run_id })}><Network size={14} /> Open temporal AML evidence</button>
  </div>;
}

function CaseTimeline({ audit = [] }) {
  if (!audit.length) return <StateMessage>Chưa có timeline event.</StateMessage>;
  return <ol className="case-timeline">{[...audit].reverse().map(entry => <li key={entry.audit_id}>
    <i aria-hidden="true" /><div><strong>{entry.action.replaceAll('_', ' ')}</strong><span>{entry.old_status || '—'} → {entry.new_status || '—'}</span><small>{formatDate(entry.created_at)} · actor #{entry.actor_user_id || 'system'}</small></div>
  </li>)}</ol>;
}

export default function SecurityTab() {
  const { token, user } = useContext(AuthContext);
  const { datasetId, dataset } = useDatasetContext();
  const initialLocation = useMemo(() => readInvestigationLocation(window.location.search), []);
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(initialLocation.page);
  const [search, setSearch] = useState(initialLocation.query);
  const [query, setQuery] = useState(initialLocation.query);
  const [status, setStatus] = useState(initialLocation.status);
  const [risk, setRisk] = useState(initialLocation.risk);
  const [selectedCaseId, setSelectedCaseId] = useState(initialLocation.caseId);
  const [caseDetail, setCaseDetail] = useState(null);
  const [sourceEvent, setSourceEvent] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState('');
  const [notice, setNotice] = useState('');
  const [priority, setPriority] = useState('P3');
  const [dueAt, setDueAt] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [comment, setComment] = useState('');
  const [disposition, setDisposition] = useState('FALSE_POSITIVE');
  const [resolutionCode, setResolutionCode] = useState('FALSE_POSITIVE');
  const [evidenceFile, setEvidenceFile] = useState(null);
  const sourceEventId = caseDetail?.source_event_ids?.[0] || caseDetail?.event_id || null;

  useEffect(() => {
    const timeout = setTimeout(() => { setPage(1); setQuery(search.trim()); }, 300);
    return () => clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    const next = buildInvestigationLocation(window.location.search, { page, caseId: selectedCaseId, query, status, risk });
    window.history.replaceState({}, '', `${window.location.pathname}${next}`);
  }, [page, query, risk, selectedCaseId, status]);

  useEffect(() => {
    const restoreLocation = () => {
      const next = readInvestigationLocation(window.location.search);
      setPage(next.page); setSearch(next.query); setQuery(next.query);
      setStatus(next.status); setRisk(next.risk); setSelectedCaseId(next.caseId);
    };
    window.addEventListener('popstate', restoreLocation);
    return () => window.removeEventListener('popstate', restoreLocation);
  }, []);

  const loadAlerts = useCallback(async (signal) => {
    const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE), dataset_id: datasetId });
    if (query) params.set('search', query);
    if (status) params.set('status', status);
    if (risk) params.set('risk_level', risk);
    setLoading(true); setError('');
    try {
      const payload = await requestJson(`/api/alerts?${params}`, token, { signal });
      setAlerts(payload.data || []); setTotal(payload.total || 0);
    } catch (fetchError) {
      if (fetchError.name !== 'AbortError') setError(fetchError.message);
    } finally { if (!signal?.aborted) setLoading(false); }
  }, [datasetId, page, query, risk, status, token]);

  const loadCase = useCallback(async (alertId, signal) => {
    if (!alertId) { setCaseDetail(null); return null; }
    setDetailLoading(true);
    try {
      const payload = await requestJson(`/api/alerts/${alertId}`, token, { signal });
      setCaseDetail(payload); setPriority(payload.priority || 'P3');
      setDueAt(toDateTimeInput(payload.due_at)); setAssigneeId(payload.assignee_id ? String(payload.assignee_id) : '');
      return payload;
    } catch (fetchError) {
      if (fetchError.name !== 'AbortError') { setError(fetchError.message); setCaseDetail(null); }
      return null;
    } finally { if (!signal?.aborted) setDetailLoading(false); }
  }, [token]);

  useEffect(() => {
    const controller = new AbortController(); loadAlerts(controller.signal);
    return () => controller.abort();
  }, [loadAlerts]);

  useEffect(() => {
    const controller = new AbortController(); loadCase(selectedCaseId, controller.signal);
    return () => controller.abort();
  }, [loadCase, selectedCaseId]);

  useEffect(() => {
    if (!sourceEventId || !caseDetail?.dataset_id) { setSourceEvent(null); return undefined; }
    const controller = new AbortController();
    const params = new URLSearchParams(); if (caseDetail.run_id) params.set('run_id', caseDetail.run_id);
    setSourceLoading(true);
    requestJson(`/api/datasets/${caseDetail.dataset_id}/events/${encodeURIComponent(sourceEventId)}?${params}`, token, { signal: controller.signal })
      .then(setSourceEvent).catch(fetchError => { if (fetchError.name !== 'AbortError') setSourceEvent(null); })
      .finally(() => { if (!controller.signal.aborted) setSourceLoading(false); });
    return () => controller.abort();
  }, [caseDetail?.dataset_id, caseDetail?.run_id, sourceEventId, token]);

  useEffect(() => {
    if (user?.role !== 'ADMIN') return undefined;
    const controller = new AbortController();
    requestJson('/api/users', token, { signal: controller.signal }).then(setUsers).catch(() => setUsers([]));
    return () => controller.abort();
  }, [token, user?.role]);

  const refreshWorkspace = useCallback(async () => {
    await Promise.all([loadAlerts(), selectedCaseId ? loadCase(selectedCaseId) : Promise.resolve()]);
  }, [loadAlerts, loadCase, selectedCaseId]);

  const mutateCase = async (label, path, method, body, successMessage) => {
    setBusy(label); setError(''); setConflict(''); setNotice('');
    try {
      await requestJson(path, token, { method, body: JSON.stringify(body) });
      setNotice(successMessage); await refreshWorkspace(); return true;
    } catch (mutationError) {
      if (isVersionConflict(mutationError.status, mutationError.message)) {
        setConflict('Case đã được cập nhật ở phiên khác. Dữ liệu mới nhất đã được tải lại; hãy kiểm tra rồi thử lại.');
        await refreshWorkspace();
      } else setError(mutationError.message);
      return false;
    } finally { setBusy(''); }
  };

  const saveMetadata = () => mutateCase('metadata', `/api/alerts/${caseDetail.alert_id}`, 'PATCH', {
    version: caseDetail.version, priority, due_at: dueAt ? new Date(dueAt).toISOString() : null,
  }, 'Priority và SLA đã được cập nhật.');
  const saveAssignment = () => mutateCase('assignment', `/api/alerts/${caseDetail.alert_id}/assignment`, 'POST', {
    version: caseDetail.version, assignee_id: assigneeId ? Number(assigneeId) : null,
  }, assigneeId ? 'Case đã được phân công.' : 'Case đã được bỏ phân công.');
  const startInvestigation = () => mutateCase('status', `/api/alerts/${caseDetail.alert_id}/status`, 'POST', {
    version: caseDetail.version, status: 'INVESTIGATING',
  }, 'Investigation đã bắt đầu.');
  const addComment = async () => {
    const saved = await mutateCase('comment', `/api/alerts/${caseDetail.alert_id}/comments`, 'POST', {
      version: caseDetail.version, body: comment.trim(),
    }, 'Investigation note đã được thêm vào timeline.');
    if (saved) setComment('');
  };
  const closeCase = () => mutateCase('disposition', `/api/alerts/${caseDetail.alert_id}/disposition`, 'POST', {
    version: caseDetail.version, disposition, resolution_code: resolutionCode,
  }, 'Case đã được kết luận và đóng.');

  const uploadEvidence = async () => {
    if (!evidenceFile) return;
    if (evidenceFile.size > 25 * 1024 * 1024) { setError('Evidence vượt giới hạn 25 MiB.'); return; }
    setBusy('evidence'); setError(''); setConflict(''); setNotice('');
    try {
      const checksum = await sha256(evidenceFile);
      const params = new URLSearchParams({
        alert_id: String(caseDetail.alert_id), filename: evidenceFile.name,
        checksum_sha256: checksum, content_type: evidenceFile.type || 'application/octet-stream',
      });
      const presign = await requestJson(`/api/evidence/presigned-url?${params}`, token);
      const upload = await fetch(presign.upload_url, { method: 'PUT', body: evidenceFile, headers: presign.required_headers });
      if (!upload.ok) throw new Error(`Evidence upload failed (${upload.status})`);
      await requestJson(`/api/alerts/${caseDetail.alert_id}/evidence/complete`, token, {
        method: 'POST', body: JSON.stringify({
          object_key: presign.object_key, version: caseDetail.version,
          checksum_sha256: checksum, content_type: evidenceFile.type || 'application/octet-stream',
        }),
      });
      setEvidenceFile(null); setNotice('Evidence đã được xác minh checksum và gắn vào case.');
      await refreshWorkspace();
    } catch (uploadError) {
      if (isVersionConflict(uploadError.status, uploadError.message)) {
        setConflict('Case thay đổi trong lúc upload. Object chưa được gắn; dữ liệu case đã được tải lại.');
        await refreshWorkspace();
      } else setError(uploadError.message);
    } finally { setBusy(''); }
  };

  const exportCsv = async () => {
    try {
      const params = new URLSearchParams({ dataset_id: datasetId });
      if (query) params.set('search', query); if (status) params.set('status', status); if (risk) params.set('risk_level', risk);
      const response = await fetch(`${apiBase()}/api/alerts/export?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error('Chỉ ADMIN có thể export');
      const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `alerts_${datasetId}.csv`; anchor.click(); URL.revokeObjectURL(url);
    } catch (exportError) { setError(exportError.message); }
  };

  const counts = useMemo(() => alerts.reduce((acc, item) => { acc[item.status] = (acc[item.status] || 0) + 1; return acc; }, {}), [alerts]);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const selectedSla = caseDetail ? caseSlaState(caseDetail.due_at, caseDetail.status) : null;
  const terminal = caseDetail ? ['RESOLVED', 'IGNORED'].includes(caseDetail.status) : false;
  const resolutions = DISPOSITION_RESOLUTIONS[disposition];

  useEffect(() => { if (!resolutions.includes(resolutionCode)) setResolutionCode(resolutions[0]); }, [disposition, resolutionCode, resolutions]);

  return <div className="page-stack investigation-page">
    <PageHeader eyebrow="Case operations" title="Investigation Workspace" description={`${dataset.label} · DS3 scope cố định · ${formatNumber(total)} case.`} actions={user?.role === 'ADMIN' ? <button className="secondary-button" onClick={exportCsv}><Download size={14} /> Export CSV</button> : null} />
    <MetricCard icon={<ShieldAlert size={17} />} label="Cases in scope" value={formatNumber(total)} detail={`${formatNumber(alerts.length)} trên trang hiện tại`} tone="blue" />
    <MetricCard icon={<Clock3 size={17} />} label="Pending" value={formatNumber(counts.PENDING || 0)} detail="Chờ phân công hoặc xử lý" tone="amber" />
    <MetricCard icon={<Search size={17} />} label="Investigating" value={formatNumber(counts.INVESTIGATING || 0)} detail="Đang phân tích" tone="violet" />
    <MetricCard icon={<CheckCircle2 size={17} />} label="Resolved" value={formatNumber(counts.RESOLVED || 0)} detail="Đã hoàn tất trên trang" tone="green" />

    {(error || conflict || notice) && <div className={`case-banner ${error || conflict ? 'case-banner-error' : 'case-banner-success'}`} role={error || conflict ? 'alert' : 'status'}>
      {conflict && <RefreshCw size={16} />}{error && <AlertTriangle size={16} />}{notice && <CheckCircle2 size={16} />}
      <span>{conflict || error || notice}</span>
    </div>}

    <Panel className="col-span-5 investigation-queue" title="Case queue" subtitle="Filters, pagination và selection được lưu trong URL">
      <div className="case-filter-grid">
        <label className="search-field"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Account, payment, rule…" aria-label="Search investigation cases" /></label>
        <select value={status} onChange={event => { setStatus(event.target.value); setPage(1); }} aria-label="Case status"><option value="">All statuses</option>{CASE_STATUSES.map(value => <option key={value}>{value}</option>)}</select>
        <select value={risk} onChange={event => { setRisk(event.target.value); setPage(1); }} aria-label="Risk level"><option value="">All risks</option>{CASE_RISK_LEVELS.map(value => <option key={value}>{value}</option>)}</select>
      </div>
      {loading ? <StateMessage type="loading">Đang tải investigation queue…</StateMessage> : alerts.length === 0 ? <StateMessage>Không có case phù hợp với bộ lọc.</StateMessage> : <div className="case-queue-list">{alerts.map(item => {
        const sla = caseSlaState(item.due_at, item.status);
        return <button key={item.alert_id} className={`case-queue-item ${selectedCaseId === item.alert_id ? 'selected' : ''}`} onClick={() => setSelectedCaseId(item.alert_id)} aria-pressed={selectedCaseId === item.alert_id}>
          <span className="case-priority-marker" data-priority={item.priority || 'P3'} /><span className="case-queue-copy"><span><strong>Case #{item.alert_id}</strong><Badge tone={STATUS_TONE[item.status]}>{item.status}</Badge></span><small>{item.account_id || 'Unknown entity'} · {item.rule_name}</small><span className="case-queue-meta"><Badge tone={PRIORITY_TONE[item.priority || 'P3']}>{item.priority || 'P3'}</Badge><span className={`sla-label sla-${sla.state}`}>{sla.label}</span><span>{formatNumber(item.risk_score, 1)} risk</span></span></span>
        </button>;
      })}</div>}
      <div className="pagination"><span>Trang {page} / {totalPages}</span><div><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>Trước</button><button disabled={page >= totalPages} onClick={() => setPage(value => value + 1)}>Sau</button></div></div>
    </Panel>

    <Panel className="col-span-7 investigation-detail" title={caseDetail ? `Case #${caseDetail.alert_id}` : 'Case detail'} subtitle={caseDetail ? `${caseDetail.rule_name} · version ${caseDetail.version}` : 'Chọn một case từ queue để bắt đầu'} action={caseDetail ? <button className="icon-button" onClick={refreshWorkspace} aria-label="Refresh case"><RefreshCw size={15} /></button> : null}>
      {detailLoading ? <StateMessage type="loading">Đang tải case record…</StateMessage> : !caseDetail ? <StateMessage>Chưa chọn case.</StateMessage> : <div className="case-workspace">
        <div className="case-hero">
          <div><div className="case-hero-badges"><Badge tone={PRIORITY_TONE[caseDetail.priority]}>{caseDetail.priority}</Badge><Badge tone={STATUS_TONE[caseDetail.status]}>{caseDetail.status}</Badge><span className={`sla-label sla-${selectedSla.state}`}>{selectedSla.label}</span></div><h3>{caseDetail.account_id || caseDetail.payment_id || caseDetail.event_id}</h3><p>{caseDetail.xai_explanation || 'Alert được tạo từ deterministic detection rule.'}</p></div>
          {caseDetail.status === 'PENDING' && <button className="primary-button" disabled={!!busy} onClick={startInvestigation}><ShieldAlert size={14} /> Start investigation</button>}
        </div>

        <dl className="case-data-grid case-summary-grid">
          <div><dt>Payment</dt><dd>{caseDetail.payment_id || '—'}</dd></div><div><dt>Amount</dt><dd>{formatNumber(caseDetail.amount, 2)}</dd></div>
          <div><dt>Risk score</dt><dd>{formatNumber(caseDetail.risk_score, 1)} · {caseDetail.risk_level}</dd></div><div><dt>Created</dt><dd>{formatDate(caseDetail.created_at)}</dd></div>
          <div><dt>Assignee</dt><dd>{caseDetail.assignee_id ? `User #${caseDetail.assignee_id}` : 'Unassigned'}</dd></div><div><dt>Trace</dt><dd>{caseDetail.trace_id || '—'}</dd></div>
        </dl>

        <section className="case-section"><header><div><h3>Priority & SLA</h3><p>Điều phối mức ưu tiên và thời hạn xử lý.</p></div></header><div className="case-form-row">
          <label><span>Priority</span><select disabled={terminal} value={priority} onChange={event => setPriority(event.target.value)}>{CASE_PRIORITIES.map(value => <option key={value}>{value}</option>)}</select></label>
          <label><span>Due at</span><input disabled={terminal} type="datetime-local" value={dueAt} onChange={event => setDueAt(event.target.value)} /></label>
          <button className="secondary-button" disabled={!!busy || terminal} onClick={saveMetadata}><Save size={14} /> Save metadata</button>
        </div></section>

        <section className="case-section"><header><div><h3>Assignment</h3><p>ADMIN phân công investigator; analyst chỉ làm việc trong phạm vi được giao.</p></div></header>{user?.role === 'ADMIN' ? <div className="case-form-row"><label className="case-grow"><span>Investigator</span><select disabled={terminal} value={assigneeId} onChange={event => setAssigneeId(event.target.value)}><option value="">Unassigned</option>{users.filter(item => ['ADMIN', 'ANALYST'].includes(item.role)).map(item => <option key={item.id} value={item.id}>{item.username} · {item.role}</option>)}</select></label><button className="secondary-button" disabled={!!busy || terminal} onClick={saveAssignment}><UserRoundCheck size={14} /> Apply assignment</button></div> : <StateMessage>Case thuộc phạm vi investigator hiện tại.</StateMessage>}</section>

        <section className="case-section"><header><div><h3>Investigation notes</h3><p>Comments append-only; mỗi note tạo một audit event.</p></div></header><div className="case-comments">{caseDetail.comments?.map(item => <article key={item.comment_id}><strong>User #{item.author_user_id}</strong><p>{item.body}</p><small>{formatDate(item.created_at)}</small></article>)}{!caseDetail.comments?.length && <StateMessage>Chưa có investigation note.</StateMessage>}</div>{!['RESOLVED', 'IGNORED'].includes(caseDetail.status) && <div className="case-comment-form"><textarea value={comment} onChange={event => setComment(event.target.value)} maxLength={2000} placeholder="Ghi nhận nhận định, bước kiểm tra hoặc quyết định…" aria-label="Investigation note" /><button className="secondary-button" disabled={!!busy || !comment.trim()} onClick={addComment}><MessageSquarePlus size={14} /> Add note</button></div>}</section>

        <section className="case-section"><header><div><h3>Evidence</h3><p>Object bất biến, tối đa 25 MiB; SHA-256 được backend xác minh.</p></div></header><div className="evidence-list">{caseDetail.evidence?.map(item => <article key={item.evidence_id}><FileCheck2 size={18} /><div><strong>{item.original_filename}</strong><span>{item.content_type} · {formatNumber(item.size_bytes)} bytes</span><code>{item.checksum_sha256}</code></div></article>)}{!caseDetail.evidence?.length && <StateMessage>Chưa có evidence file.</StateMessage>}</div>{!['RESOLVED', 'IGNORED'].includes(caseDetail.status) && <div className="evidence-upload"><input type="file" onChange={event => setEvidenceFile(event.target.files?.[0] || null)} aria-label="Evidence file" /><button className="secondary-button" disabled={!!busy || !evidenceFile} onClick={uploadEvidence}><Upload size={14} /> {busy === 'evidence' ? 'Verifying…' : 'Upload evidence'}</button></div>}</section>

        <section className="case-section"><header><div><h3>Source & graph evidence</h3><p>Liên kết case với source row PaySim và participant graph DS3.</p></div></header><SourceEvidence item={caseDetail} source={sourceEvent} loading={sourceLoading} /></section>

        {caseDetail.status === 'INVESTIGATING' && <section className="case-section case-disposition"><header><div><h3>Disposition</h3><p>Kết luận đóng case với resolution code bắt buộc.</p></div></header><div className="case-form-row"><label><span>Disposition</span><select value={disposition} onChange={event => setDisposition(event.target.value)}>{Object.keys(DISPOSITION_RESOLUTIONS).map(value => <option key={value} value={value}>{DISPOSITION_LABELS[value]}</option>)}</select></label><label><span>Resolution</span><select value={resolutionCode} onChange={event => setResolutionCode(event.target.value)}>{resolutions.map(value => <option key={value}>{value}</option>)}</select></label><button className="primary-button" disabled={!!busy} onClick={closeCase}><CheckCircle2 size={14} /> Close case</button></div></section>}

        <section className="case-section"><header><div><h3>Audit timeline</h3><p>Mọi mutation quan trọng được ghi cùng transaction.</p></div></header><CaseTimeline audit={caseDetail.audit} /></section>
        <div className="case-links"><button className="text-button" onClick={() => openWorkspace('analytics', { account: caseDetail.account_id, event: sourceEventId, run: caseDetail.run_id })}>Temporal AML evidence <ExternalLink size={12} /></button></div>
      </div>}
    </Panel>
  </div>;
}
