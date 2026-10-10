import React, { useCallback, useContext, useEffect, useState } from 'react';
import { Gauge, Power, RefreshCw, Save, Settings2 } from 'lucide-react';
import { AuthContext } from './AuthContext';
import { Badge, formatNumber, MetricCard, PageHeader, Panel, StateMessage } from './ui';

export default function RulesManagementTab() {
  const { token, user } = useContext(AuthContext);
  const [rules, setRules] = useState([]);
  const [editing, setEditing] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const base = window._env_?.API_URL || 'http://localhost:8000';

  const fetchRules = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const response = await fetch(base + '/api/rules', { headers:{ Authorization:`Bearer ${token}` } });
      if (!response.ok) throw new Error((await response.json()).detail || `Không tải được rules (${response.status})`);
      const data = await response.json(); setRules(Array.isArray(data) ? data : []);
    } catch (fetchError) { setError(fetchError.message); } finally { setLoading(false); }
  }, [base, token]);
  useEffect(() => { fetchRules(); }, [fetchRules]);

  const editRule = rule => { setEditing(rule.rule_id); setValues({ threshold:rule.threshold, window_seconds:rule.window_seconds, max_count:rule.max_count, is_active:rule.is_active, description:rule.description || '' }); setMessage(''); };
  const updateRule = async (ruleId, payload) => {
    setSaving(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${base}/api/rules/${ruleId}`, { method:'PUT', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body:JSON.stringify(payload) });
      if (!response.ok) throw new Error((await response.json()).detail || `Không cập nhật được rule (${response.status})`);
      const result = await response.json(); setMessage(result.message || 'Đã cập nhật rule'); setEditing(null); await fetchRules();
    } catch (updateError) { setError(updateError.message); } finally { setSaving(false); }
  };
  const active = rules.filter(rule => rule.is_active).length;

  return <div className="page-stack">
    <PageHeader eyebrow="Detection controls" title="Detection Rules" description="Cấu hình deterministic rules dùng cho stream processing; thay đổi được publish qua Redis." actions={<button className="secondary-button" onClick={fetchRules} disabled={loading}><RefreshCw size={14}/> Refresh</button>} />
    <MetricCard icon={<Settings2 size={17}/>} label="Configured rules" value={formatNumber(rules.length)} detail="Rule registry in PostgreSQL" tone="blue" />
    <MetricCard icon={<Power size={17}/>} label="Active" value={formatNumber(active)} detail={`${formatNumber(rules.length - active)} disabled`} tone="green" />
    <MetricCard icon={<Gauge size={17}/>} label="Average threshold" value={formatNumber(rules.length ? rules.reduce((sum, rule) => sum + Number(rule.threshold || 0), 0) / rules.length : 0, 2)} detail="Không so sánh như model score" tone="amber" />
    <MetricCard icon={<Save size={17}/>} label="Access" value={user?.role || '—'} detail="Chỉ ADMIN được chỉnh sửa" tone="violet" />
    <Panel className="col-span-12" title="Rule registry" subtitle="Threshold, time window và violation count">
      {message && <div className="inline-message success">{message}</div>}{error && <StateMessage type="error">{error}</StateMessage>}
      {loading ? <StateMessage type="loading">Đang tải detection rules…</StateMessage> : <div className="rule-list">{rules.map(rule => {
        const isEditing = editing === rule.rule_id;
        return <article className={`rule-card ${rule.is_active ? '' : 'disabled'}`} key={rule.rule_id}><div className="rule-header"><div><strong>{rule.name.replaceAll('_', ' ')}</strong><Badge tone={rule.is_active ? 'green' : 'neutral'}>{rule.is_active ? 'ACTIVE' : 'DISABLED'}</Badge><p>{rule.description || 'Không có mô tả.'}</p></div>{user?.role === 'ADMIN' && <div className="case-actions"><button className="secondary-button" onClick={() => updateRule(rule.rule_id, { is_active:!rule.is_active })}>{rule.is_active ? 'Disable' : 'Enable'}</button>{isEditing ? <button className="primary-button" disabled={saving} onClick={() => updateRule(rule.rule_id, values)}><Save size={13}/>{saving ? 'Saving…' : 'Save'}</button> : <button className="secondary-button" onClick={() => editRule(rule)}>Edit</button>}</div>}</div><div className="rule-parameters"><label><span>Threshold</span>{isEditing ? <input type="number" min="0" value={values.threshold} onChange={event => setValues(previous => ({ ...previous, threshold:Number(event.target.value) }))}/> : <strong>{formatNumber(rule.threshold, 2)}</strong>}</label><label><span>Window seconds</span>{isEditing ? <input type="number" min="1" value={values.window_seconds} onChange={event => setValues(previous => ({ ...previous, window_seconds:Number(event.target.value) }))}/> : <strong>{formatNumber(rule.window_seconds)}s</strong>}</label><label><span>Max count</span>{isEditing ? <input type="number" min="1" value={values.max_count} onChange={event => setValues(previous => ({ ...previous, max_count:Number(event.target.value) }))}/> : <strong>{formatNumber(rule.max_count)}</strong>}</label></div></article>;
      })}{!rules.length && <StateMessage>Chưa có detection rule.</StateMessage>}</div>}
    </Panel>
  </div>;
}
