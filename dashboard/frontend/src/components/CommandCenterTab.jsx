import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Database, Radio, ShieldAlert, WalletCards } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useDatasetContext } from './DatasetContext';
import { useDatasetAnalytics } from './useDatasetAnalytics';
import { Badge, formatNumber, formatPercent, MetricCard, PageHeader, Panel, StateMessage } from './ui';

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map(item => <span key={item.dataKey} style={{ color: item.color }}>{item.name}: {formatNumber(item.value, 2)}</span>)}</div>;
}

export default function CommandCenterTab({ data, tps, totalValue, sessionEvents, isConnected }) {
  const { datasetId, dataset, mode, groundTruthVisible } = useDatasetContext();
  const analytics = useDatasetAnalytics();
  const benchmark = datasetId !== 'live';

  if (benchmark && analytics.loading) return <div className="page-stack"><PageHeader eyebrow="Risk operations" title="Command Center" description={dataset.description} /><Panel className="col-span-12"><StateMessage type="loading">Đang tổng hợp dữ liệu {dataset.shortLabel}…</StateMessage></Panel></div>;
  if (benchmark && analytics.error) return <div className="page-stack"><PageHeader eyebrow="Risk operations" title="Command Center" description={dataset.description} /><Panel className="col-span-12"><StateMessage type="error">{analytics.error}</StateMessage></Panel></div>;

  const overview = analytics.overview;
  return <div className="page-stack">
    <PageHeader eyebrow="Risk operations" title="Command Center" description={benchmark ? `Ảnh chụp benchmark ${dataset.label}; thời gian theo ${dataset.timeSemantics}.` : 'Giám sát luồng payment live và trạng thái kết nối trong phiên hiện tại.'} actions={<Badge tone={benchmark ? 'amber' : isConnected ? 'green' : 'red'}>{benchmark ? mode : isConnected ? 'streaming' : 'offline'}</Badge>} />
    {benchmark ? <>
      <MetricCard icon={<Database size={17} />} label={datasetId === 'ds4_baf' ? 'Applications loaded' : 'Events loaded'} value={formatNumber(overview?.event_count)} detail={`${formatNumber(overview?.evaluated_count)} đã evaluate`} tone="blue" />
      <MetricCard icon={<ShieldAlert size={17} />} label="Ground-truth fraud" value={groundTruthVisible ? formatNumber(overview?.fraud_count) : 'Ẩn'} detail={groundTruthVisible ? `${formatPercent(overview?.fraud_rate, 3)} trên dữ liệu đã nạp` : 'Không hiển thị trong operational mode'} tone="red" />
      <MetricCard icon={<AlertTriangle size={17} />} label="Open alerts" value={formatNumber(overview?.open_alerts)} detail={`${formatNumber(overview?.alert_count)} alert tổng cộng`} tone="amber" />
      <MetricCard icon={<CheckCircle2 size={17} />} label="Detection recall" value={groundTruthVisible ? formatPercent(overview?.recall) : 'Ẩn'} detail={groundTruthVisible ? `Precision ${formatPercent(overview?.precision)}` : 'Tránh ground-truth leakage'} tone="green" />
      <Panel className="col-span-8" title="Volume & fraud theo thời gian tương đối" subtitle={`Đơn vị nguồn: ${overview?.time_unit || dataset.timeSemantics}`}>
        {analytics.timeseries.length ? <ResponsiveContainer width="100%" height={310}><AreaChart data={analytics.timeseries}><defs><linearGradient id="eventsArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#4f8cff" stopOpacity=".38" /><stop offset="1" stopColor="#4f8cff" stopOpacity=".02" /></linearGradient></defs><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="bucket" stroke="#70839e" fontSize={10} /><YAxis stroke="#70839e" fontSize={10} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="event_count" name="Events" stroke="#4f8cff" fill="url(#eventsArea)" strokeWidth={2} />{groundTruthVisible && <Area type="monotone" dataKey="fraud_count" name="Fraud" stroke="#fb7185" fill="transparent" strokeWidth={2} />}</AreaChart></ResponsiveContainer> : <StateMessage>Chưa có time series.</StateMessage>}
      </Panel>
      <Panel className="col-span-4" title="Dataset boundary" subtitle="Giới hạn diễn giải bắt buộc">
        <div className="boundary-card"><strong>{dataset.label}</strong><p>{dataset.description}</p><dl><div><dt>Time basis</dt><dd>{dataset.timeSemantics}</dd></div><div><dt>First ingest</dt><dd>{overview?.first_ingested_at ? new Date(overview.first_ingested_at).toLocaleString('vi-VN') : '—'}</dd></div><div><dt>Last ingest</dt><dd>{overview?.last_ingested_at ? new Date(overview.last_ingested_at).toLocaleString('vi-VN') : '—'}</dd></div></dl></div>
      </Panel>
    </> : <>
      <MetricCard icon={<Radio size={17} />} label="Current throughput" value={`${tps} events/s`} detail={`${formatNumber(sessionEvents)} event trong phiên`} tone="cyan" />
      <MetricCard icon={<WalletCards size={17} />} label="Observed value" value={`$${formatNumber(totalValue, 2)}`} detail="Tính từ lúc mở trang" tone="green" />
      <MetricCard icon={<Activity size={17} />} label="WebSocket" value={isConnected ? 'Connected' : 'Offline'} detail="Authenticated live channel" tone={isConnected ? 'green' : 'red'} />
      <MetricCard icon={<ShieldAlert size={17} />} label="Data source" value="Live" detail="Payment / transfer sources" tone="violet" />
      <Panel className="col-span-12" title="Live payment value" subtitle="60 sự kiện gần nhất nhận qua WebSocket">
        {data.length ? <ResponsiveContainer width="100%" height={320}><AreaChart data={data}><defs><linearGradient id="liveAmount" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#38c8e8" stopOpacity=".4" /><stop offset="1" stopColor="#38c8e8" stopOpacity=".02" /></linearGradient></defs><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey="time" stroke="#70839e" fontSize={10} /><YAxis stroke="#70839e" fontSize={10} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="amount" name="Amount" stroke="#38c8e8" fill="url(#liveAmount)" strokeWidth={2} isAnimationActive={false} /></AreaChart></ResponsiveContainer> : <StateMessage>Chưa nhận được payment event trong phiên này.</StateMessage>}
      </Panel>
    </>}
  </div>;
}
