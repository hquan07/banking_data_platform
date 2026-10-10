import React, { useMemo, useState } from 'react';
import { AlertTriangle, Crosshair, Gauge, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useDatasetContext } from './DatasetContext';
import { useDatasetAnalytics } from './useDatasetAnalytics';
import { formatNumber, formatPercent, MetricCard, PageHeader, Panel, StateMessage } from './ui';

const SEGMENT_LABELS = { amount_band: 'Amount band', transaction_type: 'Transaction type', source: 'Application source', device_os: 'Device OS', payment_type: 'Payment type', age_band: 'Customer age band' };

export default function FraudMonitoringTab() {
  const { datasetId, dataset, mode } = useDatasetContext();
  const analytics = useDatasetAnalytics();
  const segmentKeys = useMemo(() => Object.keys(analytics.segments), [analytics.segments]);
  const [chosenSegment, setChosenSegment] = useState('');
  const segment = segmentKeys.includes(chosenSegment) ? chosenSegment : segmentKeys[0];
  const rows = analytics.segments[segment] || [];

  if (datasetId === 'live') return <div className="page-stack"><PageHeader eyebrow="Detection analytics" title="Fraud Monitor" description="Live monitor chỉ hiển thị alert runtime; chọn một benchmark để xem evaluation với ground truth." /><Panel className="col-span-12"><StateMessage>Chọn DS1, DS3 hoặc DS4 trên thanh nguồn dữ liệu.</StateMessage></Panel></div>;
  if (analytics.loading) return <div className="page-stack"><PageHeader eyebrow="Detection analytics" title="Fraud Monitor" description={dataset.description} /><Panel className="col-span-12"><StateMessage type="loading">Đang tính detection metrics…</StateMessage></Panel></div>;
  if (analytics.error) return <div className="page-stack"><PageHeader eyebrow="Detection analytics" title="Fraud Monitor" description={dataset.description} /><Panel className="col-span-12"><StateMessage type="error">{analytics.error}</StateMessage></Panel></div>;

  const overview = analytics.overview;
  const matrix = overview?.confusion_matrix || {};
  return <div className="page-stack">
    <PageHeader eyebrow="Detection analytics" title="Fraud Monitor" description={`${dataset.label} · ${dataset.timeSemantics}. Ground truth chỉ hiện trong Benchmark mode.`} />
    <MetricCard icon={<Crosshair size={17} />} label="Predicted fraud" value={formatNumber(overview?.predicted_fraud)} detail={`${formatNumber(overview?.evaluated_count)} evaluated`} tone="violet" />
    <MetricCard icon={<ShieldCheck size={17} />} label="Precision" value={mode === 'benchmark' ? formatPercent(overview?.precision) : 'Ẩn'} detail={`${formatNumber(matrix.tp)} TP · ${formatNumber(matrix.fp)} FP`} tone="green" />
    <MetricCard icon={<Gauge size={17} />} label="Recall" value={mode === 'benchmark' ? formatPercent(overview?.recall) : 'Ẩn'} detail={`${formatNumber(matrix.fn)} false negatives`} tone="blue" />
    <MetricCard icon={<AlertTriangle size={17} />} label="False-positive rate" value={mode === 'benchmark' ? formatPercent(overview?.false_positive_rate, 3) : 'Ẩn'} detail={`${formatNumber(matrix.tn)} true negatives`} tone="amber" />
    <Panel className="col-span-8" title={`Fraud distribution · ${SEGMENT_LABELS[segment] || segment}`} subtitle="Event volume và ground-truth fraud trên cùng segment" action={segmentKeys.length > 1 ? <select className="compact-select" value={segment} onChange={event => setChosenSegment(event.target.value)}>{segmentKeys.map(key => <option key={key} value={key}>{SEGMENT_LABELS[key] || key}</option>)}</select> : null}>
      {rows.length ? <ResponsiveContainer width="100%" height={330}><BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 18 }}><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="label" stroke="#70839e" fontSize={10} /><YAxis stroke="#70839e" fontSize={10} /><Tooltip contentStyle={{ background: '#0d1829', border: '1px solid #263750', fontSize: 11 }} /><Legend wrapperStyle={{ fontSize: 10 }} /><Bar dataKey="event_count" name={datasetId === 'ds4_baf' ? 'Applications' : 'Events'} fill="#4f8cff" radius={[4,4,0,0]} /><Bar dataKey="fraud_count" name="Fraud" fill="#fb7185" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer> : <StateMessage>Không có segment data.</StateMessage>}
    </Panel>
    <Panel className="col-span-4" title="Confusion matrix" subtitle="Latest evaluation per event">
      <div className="confusion-matrix"><div className="matrix-label" /><div className="matrix-label">Predicted fraud</div><div className="matrix-label">Predicted normal</div><div className="matrix-label">Actual fraud</div><div className="matrix-cell matrix-good"><strong>{formatNumber(matrix.tp)}</strong><span>True positive</span></div><div className="matrix-cell matrix-bad"><strong>{formatNumber(matrix.fn)}</strong><span>False negative</span></div><div className="matrix-label">Actual normal</div><div className="matrix-cell matrix-warn"><strong>{formatNumber(matrix.fp)}</strong><span>False positive</span></div><div className="matrix-cell"><strong>{formatNumber(matrix.tn)}</strong><span>True negative</span></div></div>
    </Panel>
  </div>;
}
