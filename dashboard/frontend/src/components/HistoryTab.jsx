import React, { useContext, useEffect, useMemo, useState } from 'react';
import { Activity, Banknote, CalendarDays, ShieldAlert } from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { useDatasetContext } from './DatasetContext';
import { formatNumber, MetricCard, PageHeader, Panel, StateMessage } from './ui';
import { useDatasetAnalytics } from './useDatasetAnalytics';

export default function HistoryTab() {
  const { token } = useContext(AuthContext);
  const { datasetId, dataset, groundTruthVisible } = useDatasetContext();
  const benchmark = useDatasetAnalytics();
  const [live, setLive] = useState({ data: [], loading: datasetId === 'live', error: '' });

  useEffect(() => {
    if (datasetId !== 'live' || !token) { setLive({ data: [], loading: false, error: '' }); return undefined; }
    const controller = new AbortController(); setLive(previous => ({ ...previous, loading: true, error: '' }));
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/analytics/history', { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error((await response.json()).detail || 'Không tải được ClickHouse history'); return response.json(); })
      .then(data => { if (!Array.isArray(data)) throw new Error('History response không hợp lệ'); setLive({ data: data.map(item => ({ ...item, total_tx:Number(item.total_tx), total_alerts:Number(item.total_alerts), total_amount:Number(item.total_amount) })), loading:false, error:'' }); })
      .catch(error => { if (error.name !== 'AbortError') setLive({ data:[], loading:false, error:error.message }); });
    return () => controller.abort();
  }, [datasetId, token]);

  const rows = datasetId === 'live' ? live.data : benchmark.timeseries.map(item => ({ ...item, label: `${item.bucket} ${item.time_unit}` }));
  const loading = datasetId === 'live' ? live.loading : benchmark.loading;
  const error = datasetId === 'live' ? live.error : benchmark.error;
  const metrics = useMemo(() => rows.reduce((acc, row) => ({
    events: acc.events + Number(row.total_tx ?? row.event_count ?? 0),
    alerts: acc.alerts + Number(row.total_alerts ?? (groundTruthVisible ? row.fraud_count : 0) ?? 0),
    amount: acc.amount + Number(row.total_amount ?? 0),
  }), { events:0, alerts:0, amount:0 }), [groundTruthVisible, rows]);
  const xKey = datasetId === 'live' ? 'date' : 'label';
  const eventKey = datasetId === 'live' ? 'total_tx' : 'event_count';
  const alertKey = datasetId === 'live' ? 'total_alerts' : 'fraud_count';

  return <div className="page-stack">
    <PageHeader eyebrow="Temporal analysis" title="Historical Analytics" description={`${dataset.label} · ${datasetId === 'live' ? 'Lịch sử theo ngày từ ClickHouse.' : `Timeline theo ${dataset.timeSemantics}; fraud là ground truth.`}`} />
    <MetricCard icon={<CalendarDays size={17} />} label="Time buckets" value={formatNumber(rows.length)} detail={dataset.timeSemantics} tone="blue" />
    <MetricCard icon={<Activity size={17} />} label={datasetId === 'live' ? 'Transactions' : 'Records'} value={formatNumber(metrics.events)} detail="Trong các bucket hiện có" tone="cyan" />
    <MetricCard icon={<ShieldAlert size={17} />} label={datasetId === 'live' ? 'Alerts created' : 'Ground-truth fraud'} value={groundTruthVisible || datasetId === 'live' ? formatNumber(metrics.alerts) : 'Hidden'} detail={datasetId === 'live' ? 'Mọi status' : groundTruthVisible ? 'Không phải model prediction' : 'Operational isolation'} tone="red" />
    <MetricCard icon={<Banknote size={17} />} label="Total amount" value={formatNumber(metrics.amount, 2)} detail="Đơn vị theo source dataset" tone="green" />
    {loading ? <Panel className="col-span-12"><StateMessage type="loading">Đang tải historical analytics…</StateMessage></Panel> : error ? <Panel className="col-span-12"><StateMessage type="error">{error}</StateMessage></Panel> : rows.length === 0 ? <Panel className="col-span-12"><StateMessage>Chưa có dữ liệu lịch sử cho nguồn này.</StateMessage></Panel> : <>
      <Panel className="col-span-12" title="Volume and risk signal" subtitle={datasetId === 'live' ? 'Transaction volume và alert creation theo ngày' : 'Record volume và ground-truth fraud theo relative-time bucket'}>
        <ResponsiveContainer width="100%" height={330}><BarChart data={rows}><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey={xKey} stroke="#70839e" fontSize={9} /><YAxis yAxisId="volume" stroke="#70839e" fontSize={9} />{(datasetId === 'live' || groundTruthVisible) && <YAxis yAxisId="risk" orientation="right" stroke="#fb7185" fontSize={9} />}<Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }} /><Legend /><Bar yAxisId="volume" dataKey={eventKey} name={datasetId === 'live' ? 'Transactions' : 'Records'} fill="#4f8cff" radius={[4,4,0,0]} />{(datasetId === 'live' || groundTruthVisible) && <Bar yAxisId="risk" dataKey={alertKey} name={datasetId === 'live' ? 'Alerts' : 'Ground-truth fraud'} fill="#fb7185" radius={[4,4,0,0]} />}</BarChart></ResponsiveContainer>
      </Panel>
      <Panel className="col-span-12" title="Amount over time" subtitle="Tổng amount trong từng time bucket; không quy đổi tiền tệ giữa nguồn">
        <ResponsiveContainer width="100%" height={300}><AreaChart data={rows}><defs><linearGradient id="historyAmount" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#35d399" stopOpacity={.35}/><stop offset="95%" stopColor="#35d399" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#20314b" vertical={false} /><XAxis dataKey={xKey} stroke="#70839e" fontSize={9} /><YAxis stroke="#70839e" fontSize={9} /><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }} /><Area type="monotone" dataKey="total_amount" name="Total amount" stroke="#35d399" fill="url(#historyAmount)" strokeWidth={2}/></AreaChart></ResponsiveContainer>
      </Panel>
    </>}
  </div>;
}
