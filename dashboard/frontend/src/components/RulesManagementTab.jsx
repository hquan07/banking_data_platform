import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  Activity, BadgeCheck, Clock3, DatabaseZap, LockKeyhole, Pencil,
  Power, RefreshCw, Save, ShieldCheck, SlidersHorizontal, X,
} from 'lucide-react';
import { AuthContext } from './AuthContext';
import { Badge, formatNumber, MetricCard, PageHeader, Panel, StateMessage } from './ui';

const ruleCatalog = {
  LARGE_TRANSACTION: { family: 'Payment fraud', scope: 'Live payments', tone: 'blue', logic: 'Amount exceeds the configured value threshold.' },
  HIGH_VELOCITY: { family: 'Payment fraud', scope: 'Live payments', tone: 'blue', logic: 'Transaction count exceeds the limit inside a rolling window.' },
  STRUCTURING_SUSPICION: { family: 'AML behavior', scope: 'Live transfers', tone: 'violet', logic: 'Repeated sub-threshold transfers accumulate inside the configured window.' },
  CIRCULAR_TRANSFER: { family: 'AML graph', scope: 'Live graph', tone: 'violet', logic: 'Transfer relationships form a circular path in the live account graph.' },
  TRANSFER_CASHOUT_CHAIN: { family: 'Retired detector', scope: 'DS3 · PaySim', tone: 'neutral', logic: 'Deprecated because PaySim participant identifiers do not support this link.' },
  TRANSFER_CASHOUT_SEQUENCE: { family: 'Benchmark rule', scope: 'DS3 · PaySim', tone: 'amber', logic: 'Adjacent TRANSFER and CASH_OUT source rows share step and amount.' },
};

const fallbackMeta = { family: 'Detection rule', scope: 'Shared', tone: 'neutral', logic: 'Configured deterministic detector.' };

function formatDate(value) {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });
}

export default function RulesManagementTab() {
  const { token, user } = useContext(AuthContext);
  const [rules, setRules] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const base = window._env_?.API_URL || 'http://localhost:8000';

  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(base + '/api/rules', { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error((await response.json()).detail || `Không tải được rules (${response.status})`);
      const data = await response.json();
      const nextRules = Array.isArray(data) ? data : [];
      setRules(nextRules);
      setSelectedId(current => nextRules.some(rule => rule.rule_id === current) ? current : nextRules[0]?.rule_id ?? null);
    } catch (fetchError) {
      setError(fetchError.message);
    } finally {
      setLoading(false);
    }
  }, [base, token]);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  const selectedRule = useMemo(
    () => rules.find(rule => rule.rule_id === selectedId) || null,
    [rules, selectedId],
  );
  const active = rules.filter(rule => rule.is_active).length;
  const operational = rules.filter(rule => (ruleCatalog[rule.name]?.scope || '').startsWith('Live')).length;
  const benchmark = rules.filter(rule => (ruleCatalog[rule.name]?.scope || '').startsWith('DS')).length;

  const selectRule = rule => {
    setSelectedId(rule.rule_id);
    setEditing(false);
    setMessage('');
    setError('');
  };

  const beginEdit = () => {
    if (!selectedRule) return;
    setValues({
      threshold: selectedRule.threshold,
      window_seconds: selectedRule.window_seconds,
      max_count: selectedRule.max_count,
      description: selectedRule.description || '',
    });
    setEditing(true);
    setMessage('');
  };

  const updateRule = async (ruleId, payload) => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${base}/api/rules/${ruleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error((await response.json()).detail || `Không cập nhật được rule (${response.status})`);
      const result = await response.json();
      setMessage(result.message || 'Đã cập nhật rule');
      setEditing(false);
      await fetchRules();
    } catch (updateError) {
      setError(updateError.message);
    } finally {
      setSaving(false);
    }
  };

  const selectedMeta = selectedRule ? (ruleCatalog[selectedRule.name] || fallbackMeta) : fallbackMeta;

  return <div className="page-stack rules-page">
    <PageHeader
      eyebrow="Detection control plane"
      title="Detection Rules"
      description="Registry hiện hành cho payment fraud và AML; mỗi rule hiển thị rõ phạm vi dữ liệu và logic đang áp dụng."
      actions={<button className="secondary-button" onClick={fetchRules} disabled={loading}><RefreshCw size={14}/> Refresh registry</button>}
    />
    <MetricCard icon={<ShieldCheck size={17}/>} label="Active coverage" value={`${formatNumber(active)}/${formatNumber(rules.length)}`} detail={`${formatNumber(rules.length - active)} rule disabled`} tone="green" />
    <MetricCard icon={<Activity size={17}/>} label="Operational" value={formatNumber(operational)} detail="Live payment & transfer rules" tone="blue" />
    <MetricCard icon={<DatabaseZap size={17}/>} label="Benchmark only" value={formatNumber(benchmark)} detail="DS3 source-aware rules" tone="amber" />
    <MetricCard icon={<LockKeyhole size={17}/>} label="Change access" value={user?.role === 'ADMIN' ? 'Admin' : 'Read only'} detail="Updates publish via Redis" tone="violet" />

    <Panel className="col-span-12 rules-workspace" title="Rule registry" subtitle="Chọn một rule để xem cấu hình và phạm vi áp dụng">
      {message && <div className="inline-message success" role="status">{message}</div>}
      {error && <StateMessage type="error">{error}</StateMessage>}
      {loading ? <StateMessage type="loading">Đang tải detection rules…</StateMessage> : rules.length ? <div className="rules-layout">
        <div className="rules-index" role="list" aria-label="Detection rule registry">
          {rules.map(rule => {
            const meta = ruleCatalog[rule.name] || fallbackMeta;
            const isSelected = rule.rule_id === selectedId;
            return <button
              className={`rule-index-item${isSelected ? ' selected' : ''}${rule.is_active ? '' : ' disabled'}`}
              key={rule.rule_id}
              onClick={() => selectRule(rule)}
              type="button"
              role="listitem"
              aria-current={isSelected ? 'true' : undefined}
            >
              <span className={`rule-family-marker rule-family-${meta.tone}`} aria-hidden="true" />
              <span className="rule-index-copy">
                <span className="rule-index-title"><strong>{rule.name.replaceAll('_', ' ')}</strong><Badge tone={rule.is_active ? 'green' : 'neutral'}>{rule.is_active ? 'Active' : 'Disabled'}</Badge></span>
                <span>{meta.family} · {meta.scope}</span>
              </span>
              <span className="rule-index-id">#{rule.rule_id}</span>
            </button>;
          })}
        </div>

        {selectedRule && <article className="rule-inspector">
          <div className="rule-inspector-heading">
            <div>
              <div className="rule-inspector-badges"><Badge tone={selectedMeta.tone}>{selectedMeta.family}</Badge><Badge tone={selectedRule.is_active ? 'green' : 'neutral'}>{selectedRule.is_active ? 'Enabled' : 'Disabled'}</Badge></div>
              <h3>{selectedRule.name.replaceAll('_', ' ')}</h3>
              <p>{selectedMeta.logic}</p>
            </div>
            {user?.role === 'ADMIN' && !editing && <button className="secondary-button" onClick={beginEdit}><Pencil size={13}/> Edit config</button>}
          </div>

          <div className="rule-scope-strip">
            <span><DatabaseZap size={14}/><small>Data scope</small><strong>{selectedMeta.scope}</strong></span>
            <span><Clock3 size={14}/><small>Last updated</small><strong>{formatDate(selectedRule.updated_at)}</strong></span>
            <span><BadgeCheck size={14}/><small>Registry key</small><strong>RULE-{String(selectedRule.rule_id).padStart(3, '0')}</strong></span>
          </div>

          {editing ? <div className="rule-editor">
            <div className="rule-editor-grid">
              <label><span>Threshold</span><input type="number" min="0" step="any" value={values.threshold} onChange={event => setValues(previous => ({ ...previous, threshold: Number(event.target.value) }))}/><small>Value or score boundary stored for this detector.</small></label>
              <label><span>Window</span><div className="input-with-suffix"><input type="number" min="1" value={values.window_seconds} onChange={event => setValues(previous => ({ ...previous, window_seconds: Number(event.target.value) }))}/><em>sec</em></div><small>Event-time window used by stateful processing.</small></label>
              <label><span>Maximum count</span><input type="number" min="1" value={values.max_count} onChange={event => setValues(previous => ({ ...previous, max_count: Number(event.target.value) }))}/><small>Allowed observations before the rule fires.</small></label>
            </div>
            <label className="rule-description-field"><span>Description</span><textarea maxLength="500" value={values.description} onChange={event => setValues(previous => ({ ...previous, description: event.target.value }))}/></label>
            <div className="rule-editor-actions">
              <button className="secondary-button" onClick={() => setEditing(false)} disabled={saving}><X size={13}/> Cancel</button>
              <button className="primary-button" disabled={saving} onClick={() => updateRule(selectedRule.rule_id, values)}><Save size={13}/>{saving ? 'Saving…' : 'Save changes'}</button>
            </div>
          </div> : <>
            <div className="rule-config-grid">
              <div><span>Threshold</span><strong>{formatNumber(selectedRule.threshold, 2)}</strong><small>Stored boundary</small></div>
              <div><span>Event window</span><strong>{formatNumber(selectedRule.window_seconds)}s</strong><small>Event-time duration</small></div>
              <div><span>Maximum count</span><strong>{formatNumber(selectedRule.max_count)}</strong><small>Trigger limit</small></div>
            </div>
            <div className="rule-description"><SlidersHorizontal size={16}/><div><span>Registry description</span><p>{selectedRule.description || 'Không có mô tả.'}</p></div></div>
            {user?.role === 'ADMIN' && <div className="rule-status-control">
              <div><Power size={16}/><span><strong>{selectedRule.is_active ? 'Rule is enabled' : 'Rule is disabled'}</strong><small>{selectedRule.is_active ? 'Processor can evaluate this rule.' : 'Processor will not evaluate this rule.'}</small></span></div>
              <button className={selectedRule.is_active ? 'secondary-button danger-button' : 'primary-button'} disabled={saving} onClick={() => updateRule(selectedRule.rule_id, { is_active: !selectedRule.is_active })}>{selectedRule.is_active ? 'Disable rule' : 'Enable rule'}</button>
            </div>}
          </>}
        </article>}
      </div> : <StateMessage>Chưa có detection rule.</StateMessage>}
    </Panel>
  </div>;
}
