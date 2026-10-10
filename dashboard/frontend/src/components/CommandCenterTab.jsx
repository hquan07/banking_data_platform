import React, { useContext, useEffect, useState } from 'react';
import { Activity, CheckCircle2, Database, Gauge, ShieldAlert } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { useDatasetContext } from './DatasetContext';

function formatNumber(value) {
  return value === null || value === undefined ? '—' : Number(value).toLocaleString('vi-VN');
}

function Metric({ icon, label, value, tone = '' }) {
  return (
    <div className="metric-card">
      <div className="metric-header">{icon}<span>{label}</span></div>
      <div className={`metric-value ${tone}`}>{value}</div>
    </div>
  );
}

export default function CommandCenterTab({ data, tps, totalValue, isConnected }) {
  const { token } = useContext(AuthContext);
  const { datasetId, dataset, mode } = useDatasetContext();
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (datasetId === 'live' || !token) {
      setStatus(null);
      setError('');
      return undefined;
    }
    const controller = new AbortController();
    fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/datasets/status`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    })
      .then(async response => {
        if (!response.ok) throw new Error('Không tải được trạng thái dataset');
        return response.json();
      })
      .then(rows => setStatus(rows.find(row => row.dataset_id === datasetId) || null))
      .catch(fetchError => { if (fetchError.name !== 'AbortError') setError(fetchError.message); })
      .finally(() => { if (!controller.signal.aborted) setError(previous => previous); });
    return () => controller.abort();
  }, [datasetId, token]);

  const benchmarkStatus = status || {};
  const isBenchmark = datasetId !== 'live';

  return (
    <div className="grid command-center">
      {isBenchmark ? (
        <>
          <Metric icon={<Database size={20} />} label="Dataset events đã nạp" value={formatNumber(benchmarkStatus.event_count)} />
          <Metric icon={<ShieldAlert size={20} />} label="Ground-truth fraud" value={mode === 'benchmark' ? formatNumber(benchmarkStatus.fraud_count) : 'Ẩn'} tone="metric-warning" />
          <Metric icon={<Gauge size={20} />} label="Fraud rate" value={mode === 'benchmark' && benchmarkStatus.event_count ? `${((benchmarkStatus.fraud_count / benchmarkStatus.event_count) * 100).toFixed(3)}%` : 'Ẩn'} />
          <div className="panel col-span-12 command-context-panel">
            <div className="command-context-heading">
              <div>
                <h2 className="panel-title">{dataset.label}</h2>
                <p>{dataset.description}</p>
              </div>
              <span className={`context-mode context-mode-${mode}`}>{mode === 'benchmark' ? 'Benchmark / Evaluation' : 'Operational'}</span>
            </div>
            {error && <p role="alert" className="dataset-error">{error}</p>}
            <div className="dataset-metric-grid">
              <div><span>Trạng thái</span><strong>{benchmarkStatus.status === 'loaded' ? 'Loaded' : 'Chưa nạp'}</strong></div>
              <div><span>Time semantics</span><strong>{dataset.timeSemantics}</strong></div>
              <div><span>First ingested</span><strong>{benchmarkStatus.first_ingested_at ? new Date(benchmarkStatus.first_ingested_at).toLocaleString('vi-VN') : '—'}</strong></div>
              <div><span>Last ingested</span><strong>{benchmarkStatus.last_ingested_at ? new Date(benchmarkStatus.last_ingested_at).toLocaleString('vi-VN') : '—'}</strong></div>
            </div>
            <p className="dataset-panel-note">
              {mode === 'benchmark'
                ? 'Ground-truth chỉ dùng để đánh giá benchmark, không được coi là tín hiệu runtime.'
                : 'Operational view không hiển thị ground-truth để tránh leakage vào quy trình điều tra.'}
            </p>
          </div>
        </>
      ) : (
        <>
          <Metric icon={<Activity size={20} />} label="Streaming TPS" value={`${tps} tx/s`} />
          <Metric icon={<Gauge size={20} />} label="Giá trị phiên hiện tại" value={`$${totalValue.toLocaleString()}`} tone="metric-success" />
          <Metric icon={<CheckCircle2 size={20} />} label="WebSocket" value={isConnected ? 'Đã kết nối' : 'Mất kết nối'} tone={isConnected ? 'metric-success' : 'metric-danger'} />
          <div className="panel col-span-12">
            <h2 className="panel-title">Giá trị thanh toán qua luồng sự kiện</h2>
            {data.length === 0 ? (
              <div role="status" className="dataset-empty">Chưa có sự kiện thanh toán từ nguồn dữ liệu.</div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={data}>
                  <defs><linearGradient id="commandAmount" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} /><stop offset="95%" stopColor="#3b82f6" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(20, 26, 40, 0.9)', borderColor: 'rgba(255,255,255,0.1)' }} />
                  <Area type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={2} fill="url(#commandAmount)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}
    </div>
  );
}

