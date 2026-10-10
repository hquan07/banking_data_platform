import React, { useContext, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronUp, Clock3, Download, Search, ShieldAlert } from 'lucide-react';
import { AuthContext } from './AuthContext';
import { useDatasetContext } from './DatasetContext';
import KYCProfile from './KYCProfile';
import { Badge, formatNumber, MetricCard, PageHeader, Panel, StateMessage } from './ui';

const PAGE_SIZE = 12;
const STATUS_TONE = { PENDING: 'amber', INVESTIGATING: 'blue', RESOLVED: 'green', IGNORED: 'neutral' };

export default function SecurityTab() {
  const { token, user } = useContext(AuthContext);
  const { datasetId, dataset } = useDatasetContext();
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [risk, setRisk] = useState('');
  const [expanded, setExpanded] = useState(null);
  const [note, setNote] = useState('');
  const [kycAccountId, setKycAccountId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { const timeout = setTimeout(() => { setPage(1); setQuery(search.trim()); }, 300); return () => clearTimeout(timeout); }, [search]);

  const loadAlerts = () => {
    const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) });
    if (datasetId !== 'live') params.set('dataset_id', datasetId);
    if (query) params.set('search', query);
    if (status) params.set('status', status);
    if (risk) params.set('risk_level', risk);
    setLoading(true); setError('');
    fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts?${params}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async response => { if (!response.ok) throw new Error((await response.json()).detail || `Không tải được alerts (${response.status})`); return response.json(); })
      .then(payload => { setAlerts(payload.data || []); setTotal(payload.total || 0); })
      .catch(fetchError => setError(fetchError.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadAlerts, [datasetId, page, query, risk, status, token]);

  const counts = useMemo(() => alerts.reduce((acc, item) => { acc[item.status] = (acc[item.status] || 0) + 1; return acc; }, {}), [alerts]);
  const updateStatus = async (item, nextStatus) => {
    try {
      const response = await fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts/${item.alert_id}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: nextStatus, version: item.version, ...(note.trim() ? { notes: note.trim() } : {}) }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || 'Không cập nhật được case');
      setExpanded(null); setNote(''); loadAlerts();
    } catch (updateError) { setError(updateError.message); }
  };
  const exportCsv = async () => {
    try {
      const response = await fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts/export`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error('Chỉ ADMIN có thể export');
      const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'alerts_export.csv'; anchor.click(); URL.revokeObjectURL(url);
    } catch (exportError) { setError(exportError.message); }
  };

  return <div className="page-stack">
    {kycAccountId && <KYCProfile accountId={kycAccountId} onClose={() => setKycAccountId(null)} />}
    <PageHeader eyebrow="Case operations" title="Investigation Queue" description={`${dataset.label} · ${formatNumber(total)} case phù hợp với phạm vi hiện tại.`} actions={user?.role === 'ADMIN' ? <button className="secondary-button" onClick={exportCsv}><Download size={14} /> Export CSV</button> : null} />
    <MetricCard icon={<ShieldAlert size={17} />} label="Cases in scope" value={formatNumber(total)} detail={`${formatNumber(alerts.length)} hiển thị trên trang`} tone="blue" />
    <MetricCard icon={<Clock3 size={17} />} label="Pending on page" value={formatNumber(counts.PENDING || 0)} detail="Chờ analyst nhận xử lý" tone="amber" />
    <MetricCard icon={<Search size={17} />} label="Investigating" value={formatNumber(counts.INVESTIGATING || 0)} detail="Đang được phân tích" tone="violet" />
    <MetricCard icon={<CheckCircle2 size={17} />} label="Resolved on page" value={formatNumber(counts.RESOLVED || 0)} detail="Đã hoàn tất điều tra" tone="green" />
    <Panel className="col-span-12" title="Alert cases" subtitle="Tìm theo account, payment hoặc detection rule">
      <div className="filter-bar"><label className="search-field"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Tìm account, payment, rule…" /></label><select value={status} onChange={event => { setStatus(event.target.value); setPage(1); }}><option value="">Tất cả trạng thái</option><option>PENDING</option><option>INVESTIGATING</option><option>RESOLVED</option><option>IGNORED</option></select><select value={risk} onChange={event => { setRisk(event.target.value); setPage(1); }}><option value="">Tất cả risk</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></div>
      {error && <StateMessage type="error">{error}</StateMessage>}
      {loading ? <StateMessage type="loading">Đang tải investigation queue…</StateMessage> : alerts.length === 0 ? <StateMessage>Không có case phù hợp với bộ lọc.</StateMessage> : <div className="dataset-table-wrap"><table className="case-table"><thead><tr><th>Case</th><th>Source</th><th>Entity</th><th>Rule</th><th>Risk</th><th>Status</th><th>Created</th><th /></tr></thead><tbody>{alerts.map(item => <React.Fragment key={item.alert_id}><tr><td><strong>#{item.alert_id}</strong><small>{item.payment_id || item.event_id || '—'}</small></td><td><Badge tone={item.dataset_id ? 'amber' : 'green'}>{item.dataset_id || 'live'}</Badge></td><td>{item.account_id ? datasetId === 'live' ? <button className="text-button" onClick={() => setKycAccountId(item.account_id)}>{item.account_id}</button> : item.account_id : '—'}</td><td>{item.rule_name}</td><td><span className={`risk-score risk-${String(item.risk_level || '').toLowerCase()}`}>{formatNumber(item.risk_score, 1)}</span></td><td><Badge tone={STATUS_TONE[item.status]}>{item.status}</Badge></td><td>{new Date(item.created_at).toLocaleString('vi-VN')}</td><td><button className="icon-button" onClick={() => { setExpanded(expanded === item.alert_id ? null : item.alert_id); setNote(item.notes || ''); }} aria-label={`Chi tiết case ${item.alert_id}`}>{expanded === item.alert_id ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button></td></tr>{expanded === item.alert_id && <tr className="case-detail-row"><td colSpan="8"><div className="case-detail"><div><span className="detail-label">XAI / evidence</span><p>{item.xai_explanation || 'Không có model explanation; alert được tạo từ rule deterministic.'}</p><small>Trace: {item.trace_id || '—'}</small></div><div><span className="detail-label">Investigation note</span><textarea value={note} onChange={event => setNote(event.target.value)} placeholder="Ghi nhận kết quả điều tra…" maxLength={1000} /></div><div className="case-actions">{item.status === 'PENDING' && <button className="primary-button" onClick={() => updateStatus(item, 'INVESTIGATING')}>Start investigation</button>}{item.status === 'INVESTIGATING' && <button className="primary-button" onClick={() => updateStatus(item, 'RESOLVED')}>Resolve</button>}{['PENDING','INVESTIGATING'].includes(item.status) && <button className="secondary-button" onClick={() => updateStatus(item, 'IGNORED')}>Ignore</button>}</div></div></td></tr>}</React.Fragment>)}</tbody></table></div>}
      <div className="pagination"><span>Trang {page} / {Math.max(1, Math.ceil(total / PAGE_SIZE))}</span><div><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>Trước</button><button disabled={page * PAGE_SIZE >= total} onClick={() => setPage(value => value + 1)}>Sau</button></div></div>
    </Panel>
  </div>;
}
