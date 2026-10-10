import React, { useContext, useEffect, useMemo, useState } from 'react';
import { Activity, Database, Fingerprint, Layers3 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { DATASET_DEFINITIONS, useDatasetContext } from './DatasetContext';
import { Badge, formatNumber, formatPercent, MetricCard, PageHeader, Panel, StateMessage } from './ui';
import { useDatasetAnalytics } from './useDatasetAnalytics';

const SOURCE_LABELS = {
  anonymized_real: 'Anonymized real-world', synthetic_simulation: 'Synthetic simulation',
  privacy_preserving_synthetic: 'Privacy-preserving synthetic',
};

const EMPTY = { status: [], performance: [], rules: [], models: [], balance: null, account: null, behavior: null };

export default function DatasetsTab() {
  const { token } = useContext(AuthContext);
  const { datasetId, dataset } = useDatasetContext();
  const analytics = useDatasetAnalytics();
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [warnings, setWarnings] = useState([]);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    const base = window._env_?.API_URL || 'http://localhost:8000';
    const paths = {
      status: '/api/datasets/status', performance: '/api/datasets/performance',
      rules: '/api/datasets/rule-hits', models: '/api/datasets/model-candidates',
      ...(datasetId === 'ds3_paysim' ? { balance: '/api/datasets/balance-anomalies' } : {}),
      ...(datasetId === 'ds4_baf' ? { account: '/api/datasets/account-risk', behavior: '/api/datasets/behavior-distributions' } : {}),
    };
    setLoading(true); setWarnings([]);
    Promise.allSettled(Object.entries(paths).map(async ([key, path]) => {
      const response = await fetch(base + path, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal });
      if (!response.ok) throw new Error(`${key}: HTTP ${response.status}`);
      return [key, await response.json()];
    })).then(results => {
      if (controller.signal.aborted) return;
      const next = { ...EMPTY }; const failed = [];
      results.forEach(result => { if (result.status === 'fulfilled') next[result.value[0]] = result.value[1]; else failed.push(result.reason.message); });
      setData(next); setWarnings(failed);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [datasetId, token]);

  const overview = analytics.overview;
  const scopedPerformance = useMemo(() => data.performance.filter(row => row.dataset_id === datasetId), [data.performance, datasetId]);
  const scopedRules = useMemo(() => data.rules.filter(row => row.dataset_id === datasetId), [data.rules, datasetId]);
  const scopedModels = useMemo(() => data.models.filter(row => row.dataset_id === datasetId), [data.models, datasetId]);
  const primarySegment = datasetId === 'ds1_creditcard' ? 'amount_band' : datasetId === 'ds3_paysim' ? 'transaction_type' : 'source';
  const segmentData = analytics.segments[primarySegment] || [];
  const velocityMax = Math.max(0, ...(data.behavior?.velocity_heatmap || []).map(item => item.count));

  return <div className="page-stack">
    <PageHeader eyebrow="Data estate" title="Data Sources" description="Provenance, coverage và dataset-native diagnostics; không nối danh tính giữa các benchmark độc lập." />
    <MetricCard icon={<Database size={17} />} label="Sources loaded" value={`${data.status.filter(item => item.status === 'loaded').length}/3`} detail="Benchmark sources in PostgreSQL" tone="blue" />
    <MetricCard icon={<Layers3 size={17} />} label="Selected records" value={datasetId === 'live' ? 'Live' : formatNumber(overview?.event_count)} detail={dataset.timeSemantics} tone="cyan" />
    <MetricCard icon={<Fingerprint size={17} />} label="Ground truth" value={datasetId === 'live' ? 'Hidden' : formatNumber(overview?.fraud_count)} detail={datasetId === 'live' ? 'Operational isolation' : formatPercent(overview?.fraud_rate)} tone="red" />
    <MetricCard icon={<Activity size={17} />} label="Evaluated" value={datasetId === 'live' ? 'N/A' : formatNumber(overview?.evaluated_count)} detail={datasetId === 'live' ? 'Streaming source' : `${formatNumber(overview?.predicted_fraud)} predicted fraud`} tone="green" />

    {warnings.length > 0 && <Panel className="col-span-12"><StateMessage type="error">Một số nguồn phụ chưa sẵn sàng: {warnings.join(' · ')}</StateMessage></Panel>}
    <Panel className="col-span-12" title="Dataset catalog" subtitle="Trạng thái nạp và ranh giới provenance">
      {loading && !data.status.length ? <StateMessage type="loading">Đang đọc data catalog…</StateMessage> : <div className="dataset-status-grid">{data.status.map(item => {
        const definition = DATASET_DEFINITIONS[item.dataset_id];
        return <article className={`dataset-card ${item.status === 'loaded' ? 'loaded' : ''}`} key={item.dataset_id}><div className="dataset-card-title"><Database size={16} /><strong>{definition?.shortLabel || item.dataset_id}</strong><Badge tone={item.status === 'loaded' ? 'green' : 'neutral'}>{item.status}</Badge></div><span className="dataset-kind">{SOURCE_LABELS[item.source_kind] || item.source_kind}</span><p>{definition?.description}</p><dl><div><dt>Records</dt><dd>{formatNumber(item.event_count)}</dd></div><div><dt>Ground truth</dt><dd>{formatNumber(item.fraud_count)}</dd></div><div><dt>Last ingest</dt><dd>{item.last_ingested_at ? new Date(item.last_ingested_at).toLocaleString('vi-VN') : '—'}</dd></div></dl></article>;
      })}</div>}
    </Panel>

    {datasetId === 'live' ? <Panel className="col-span-12" title="Live source boundary"><StateMessage>Live events phục vụ vận hành; ground truth và benchmark evaluation không được suy diễn từ nguồn này. Chọn DS1, DS3 hoặc DS4 để xem data diagnostics.</StateMessage></Panel> : analytics.loading ? <Panel className="col-span-12"><StateMessage type="loading">Đang tải diagnostics cho {dataset.label}…</StateMessage></Panel> : analytics.error ? <Panel className="col-span-12"><StateMessage type="error">{analytics.error}</StateMessage></Panel> : <>
      <Panel className="col-span-8" title={`${dataset.shortLabel} · ${primarySegment.replace('_', ' ')}`} subtitle="Phân bố record và ground-truth fraud theo trường gốc">
        {segmentData.length ? <ResponsiveContainer width="100%" height={300}><BarChart data={segmentData}><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="label" stroke="#70839e" fontSize={9} /><YAxis stroke="#70839e" fontSize={9} /><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }} /><Bar dataKey="event_count" name="Records" fill="#4f8cff" radius={[4,4,0,0]} /><Bar dataKey="fraud_count" name="Fraud" fill="#fb7185" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer> : <StateMessage>Chưa có segment data.</StateMessage>}
      </Panel>
      <Panel className="col-span-4" title="Evaluation registry" subtitle="Phiên bản evaluator đã chạy">
        {scopedPerformance.length ? <div className="dataset-table-wrap"><table><thead><tr><th>Version</th><th>TP / FP</th><th>FN / TN</th></tr></thead><tbody>{scopedPerformance.map(row => <tr key={row.evaluator_version}><td>{row.evaluator_version}</td><td>{formatNumber(row.true_positive)} / {formatNumber(row.false_positive)}</td><td>{formatNumber(row.false_negative)} / {formatNumber(row.true_negative)}</td></tr>)}</tbody></table></div> : <StateMessage>Chưa có evaluation.</StateMessage>}
      </Panel>
      <Panel className="col-span-6" title="Alert rules" subtitle="Alert thực tế sinh ra trong đúng dataset scope">
        {scopedRules.length ? <div className="dataset-table-wrap"><table><thead><tr><th>Rule</th><th>Alerts</th></tr></thead><tbody>{scopedRules.map(row => <tr key={row.rule}><td>{row.rule}</td><td>{formatNumber(row.count)}</td></tr>)}</tbody></table></div> : <StateMessage>Không có rule hit trong dataset này.</StateMessage>}
      </Panel>
      <Panel className="col-span-6" title="Model candidates" subtitle="Artifact audit; không đồng nghĩa đã deploy production">
        {scopedModels.length ? scopedModels.map(model => <article className="model-candidate" key={model.version}><div className="model-candidate-heading"><div><strong>{model.version}</strong><span>{model.algorithm} · {formatNumber(model.train_rows)} train rows</span></div><Badge tone={model.production_eligible ? 'green' : 'red'}>{model.decision}</Badge></div><p className="dataset-panel-note">PR-AUC {formatNumber(model.metrics.pr_auc, 4)} · Precision {formatPercent(model.metrics.precision)} · Recall {formatPercent(model.metrics.recall)}</p></article>) : <StateMessage>Chưa có model candidate được audit.</StateMessage>}
      </Panel>

      {datasetId === 'ds3_paysim' && <Panel className="col-span-12" title="PaySim balance signals" subtitle="Kết quả từ latest evaluation cho từng event">{data.balance ? <div className="dataset-metric-grid"><div><span>Balance mismatch</span><strong>{formatNumber(data.balance.balance_mismatch)}</strong></div><div><span>Zero drain</span><strong>{formatNumber(data.balance.zero_drain)}</strong></div><div><span>Source flagged</span><strong>{formatNumber(data.balance.source_system_flagged)}</strong></div><div><span>Flag true / false positive</span><strong>{formatNumber(data.balance.source_flag_true_positive)} / {formatNumber(data.balance.source_flag_false_positive)}</strong></div></div> : <StateMessage>Không có balance diagnostics.</StateMessage>}</Panel>}

      {datasetId === 'ds4_baf' && <><Panel className="col-span-6" title="Application profile" subtitle="Thống kê mô tả; không tự tạo risk label">{data.account ? <dl className="dataset-summary-list"><div><dt>Average income</dt><dd>{formatNumber(data.account.average_income, 3)}</dd></div><div><dt>Credit-risk score</dt><dd>{formatNumber(data.account.average_credit_risk_score, 2)}</dd></div><div><dt>Session minutes</dt><dd>{formatNumber(data.account.average_session_minutes, 2)}</dd></div><div><dt>Foreign requests</dt><dd>{formatNumber(data.account.foreign_request_count)}</dd></div></dl> : <StateMessage>Không có application profile.</StateMessage>}</Panel><Panel className="col-span-6" title="Velocity 6h × 24h" subtitle="25 ô quantile, fraud count giữ nguyên ground truth">{data.behavior?.velocity_heatmap?.length ? <div className="velocity-heatmap">{data.behavior.velocity_heatmap.map(cell => <div className="velocity-cell" key={`${cell.velocity_6h_quantile}-${cell.velocity_24h_quantile}`} style={{ background:`rgba(79,140,255,${.08 + (velocityMax ? cell.count / velocityMax : 0) * .72})` }}><small>Q{cell.velocity_6h_quantile}/Q{cell.velocity_24h_quantile}</small><strong>{formatNumber(cell.count)}</strong><span>{formatNumber(cell.fraud_count)} fraud</span></div>)}</div> : <StateMessage>Không có behavior distribution.</StateMessage>}</Panel></>}
    </>}
  </div>;
}
