import React, { useContext, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Database, Gauge, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { AuthContext } from './AuthContext';


const SOURCE_LABELS = {
  anonymized_real: 'Giao dịch ẩn danh',
  synthetic_simulation: 'Mô phỏng synthetic',
  privacy_preserving_synthetic: 'Synthetic bảo vệ riêng tư',
};

const ENDPOINTS = {
  status: '/api/datasets/status',
  performance: '/api/datasets/performance',
  rules: '/api/datasets/rule-hits',
  types: '/api/datasets/transaction-types',
  balance: '/api/datasets/balance-anomalies',
  velocity: '/api/datasets/velocity-summary',
  account: '/api/datasets/account-risk',
};

function Empty({ children }) {
  return <div className="dataset-empty">{children}</div>;
}

function formatNumber(value, maximumFractionDigits = 0) {
  if (value === null || value === undefined) return '—';
  return Number(value).toLocaleString('vi-VN', { maximumFractionDigits });
}

export default function DatasetsTab() {
  const { token } = useContext(AuthContext);
  const [data, setData] = useState({
    status: [], performance: [], rules: [], types: [], balance: null, velocity: null, account: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    const load = async () => {
      const entries = await Promise.all(Object.entries(ENDPOINTS).map(async ([key, path]) => {
        const response = await fetch(baseUrl + path, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Không tải được ${key} (${response.status})`);
        return [key, await response.json()];
      }));
      setData(Object.fromEntries(entries));
    };
    setLoading(true);
    setError('');
    load()
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token]);

  const loadedCount = useMemo(
    () => data.status.filter(item => item.status === 'loaded').length,
    [data.status],
  );

  if (loading) return <div role="status" className="dataset-empty">Đang tải trạng thái dataset...</div>;
  if (error) return <div role="alert" className="dataset-empty dataset-error"><AlertTriangle size={20} /> {error}</div>;

  return (
    <div className="grid dataset-dashboard">
      <section className="panel col-span-12">
        <div className="dataset-heading">
          <div>
            <h2 className="panel-title">Dataset Monitor</h2>
            <p>Theo dõi dữ liệu đã replay; các dataset độc lập không được ghép thành một khách hàng chung.</p>
          </div>
          <div className="dataset-loaded-count"><Database size={18} /> {loadedCount}/3 nguồn đã nạp</div>
        </div>
        <div className="dataset-status-grid">
          {data.status.map(item => {
            const loaded = item.status === 'loaded';
            const fraudRate = item.event_count ? (item.fraud_count / item.event_count) * 100 : null;
            return (
              <article className={`dataset-card ${loaded ? 'loaded' : ''}`} key={item.dataset_id}>
                <div className="dataset-card-title">
                  {loaded ? <CheckCircle2 size={18} /> : <Database size={18} />}
                  <strong>{item.name}</strong>
                </div>
                <span className="dataset-kind">{SOURCE_LABELS[item.source_kind] || item.source_kind}</span>
                <dl>
                  <div><dt>Events</dt><dd>{formatNumber(item.event_count)}</dd></div>
                  <div><dt>Ground-truth fraud</dt><dd>{formatNumber(item.fraud_count)}</dd></div>
                  <div><dt>Fraud rate</dt><dd>{fraudRate === null ? '—' : `${formatNumber(fraudRate, 3)}%`}</dd></div>
                </dl>
              </article>
            );
          })}
        </div>
      </section>

      <section className="panel col-span-6">
        <h2 className="panel-title"><ShieldCheck size={18} /> Evaluation theo nguồn</h2>
        {data.performance.length ? (
          <div className="dataset-table-wrap">
            <table className="dataset-table">
              <thead><tr><th>Dataset</th><th>Version</th><th>TP</th><th>FP</th><th>TN</th><th>FN</th></tr></thead>
              <tbody>{data.performance.map(row => (
                <tr key={`${row.dataset_id}-${row.evaluator_version}`}>
                  <td>{row.dataset_id}</td><td>{row.evaluator_version}</td>
                  <td>{formatNumber(row.true_positive)}</td><td>{formatNumber(row.false_positive)}</td>
                  <td>{formatNumber(row.true_negative)}</td><td>{formatNumber(row.false_negative)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <Empty>Chưa có evaluation. Hãy replay dataset để bắt đầu đo.</Empty>}
      </section>

      <section className="panel col-span-6">
        <h2 className="panel-title"><Gauge size={18} /> Rule hits theo dataset</h2>
        {data.rules.length ? (
          <div className="dataset-table-wrap">
            <table className="dataset-table">
              <thead><tr><th>Dataset</th><th>Rule</th><th>Số alert</th></tr></thead>
              <tbody>{data.rules.map(row => (
                <tr key={`${row.dataset_id}-${row.rule}`}>
                  <td>{row.dataset_id}</td><td>{row.rule}</td><td>{formatNumber(row.count)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <Empty>Chưa có rule hit từ dataset.</Empty>}
      </section>

      <section className="panel col-span-8 dataset-chart-panel">
        <h2 className="panel-title">PaySim — phân bố loại giao dịch</h2>
        {data.types.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.types} margin={{ top: 8, right: 16, left: 8, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="transaction_type" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #334155' }} />
              <Bar dataKey="count" name="Events" fill="#3b82f6" radius={[5, 5, 0, 0]} />
              <Bar dataKey="fraud_count" name="Ground-truth fraud" fill="#ef4444" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <Empty>Chưa có dữ liệu PaySim.</Empty>}
      </section>

      <section className="panel col-span-4">
        <h2 className="panel-title">BAF — velocity summary</h2>
        {data.velocity ? (
          <dl className="dataset-summary-list">
            <div><dt>Velocity 6h trung bình</dt><dd>{formatNumber(data.velocity.velocity_6h_avg, 2)}</dd></div>
            <div><dt>Velocity 6h P50</dt><dd>{formatNumber(data.velocity.velocity_6h_p50, 2)}</dd></div>
            <div><dt>Velocity 6h P95</dt><dd>{formatNumber(data.velocity.velocity_6h_p95, 2)}</dd></div>
            <div><dt>Velocity 24h trung bình</dt><dd>{formatNumber(data.velocity.velocity_24h_avg, 2)}</dd></div>
            <div><dt>Velocity 4w trung bình</dt><dd>{formatNumber(data.velocity.velocity_4w_avg, 2)}</dd></div>
          </dl>
        ) : <Empty>Chưa có dữ liệu BAF.</Empty>}
      </section>

      <section className="panel col-span-12 dataset-chart-panel">
        <h2 className="panel-title">PaySim — balance anomaly</h2>
        {data.balance ? (
          <>
            <div className="dataset-metric-grid">
              <div><span>Events</span><strong>{formatNumber(data.balance.total_events)}</strong></div>
              <div><span>Đã evaluate</span><strong>{formatNumber(data.balance.evaluated_events)}</strong></div>
              <div><span>Rule dự đoán fraud</span><strong>{formatNumber(data.balance.predicted_fraud)}</strong></div>
              <div><span>Ground-truth fraud</span><strong>{formatNumber(data.balance.ground_truth_fraud)}</strong></div>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={[
                { signal: 'Balance mismatch', count: data.balance.balance_mismatch },
                { signal: 'Zero drain', count: data.balance.zero_drain },
                { signal: 'Source flagged', count: data.balance.source_system_flagged },
              ]} margin={{ top: 12, right: 16, left: 8, bottom: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="signal" stroke="#94a3b8" />
                <YAxis allowDecimals={false} stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #334155' }} />
                <Bar dataKey="count" name="Events" fill="#f59e0b" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="dataset-panel-note">
              Source flag: {formatNumber(data.balance.source_flag_true_positive)} true positive,
              {' '}{formatNumber(data.balance.source_flag_false_positive)} false positive.
              Rule metrics dùng evaluation mới nhất của từng event.
            </p>
          </>
        ) : <Empty>Chưa có dữ liệu PaySim để phân tích số dư.</Empty>}
      </section>

      <section className="panel col-span-12 dataset-chart-panel">
        <h2 className="panel-title">BAF — account application analytics</h2>
        {data.account ? (
          <>
            <div className="dataset-metric-grid">
              <div><span>Applications</span><strong>{formatNumber(data.account.total_applications)}</strong></div>
              <div><span>Ground-truth fraud</span><strong>{formatNumber(data.account.fraud_count)}</strong></div>
              <div><span>Fraud rate</span><strong>{formatNumber(data.account.fraud_rate * 100, 2)}%</strong></div>
              <div><span>Foreign requests</span><strong>{formatNumber(data.account.foreign_request_count)}</strong></div>
              <div><span>Credit score TB</span><strong>{formatNumber(data.account.average_credit_risk_score, 2)}</strong></div>
              <div><span>Session TB</span><strong>{formatNumber(data.account.average_session_minutes, 2)} phút</strong></div>
              <div><span>Income TB</span><strong>{formatNumber(data.account.average_income, 3)}</strong></div>
              <div><span>Name/email similarity</span><strong>{formatNumber(data.account.average_name_email_similarity, 3)}</strong></div>
            </div>
            <div className="dataset-split-grid">
              <div>
                <h3>Theo application source</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={data.account.by_source} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="source" stroke="#94a3b8" />
                    <YAxis allowDecimals={false} stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: '#111827', border: '1px solid #334155' }} />
                    <Bar dataKey="count" name="Applications" fill="#8b5cf6" radius={[5, 5, 0, 0]} />
                    <Bar dataKey="fraud_count" name="Fraud" fill="#ef4444" radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div>
                <h3>Theo device OS</h3>
                <div className="dataset-table-wrap">
                  <table className="dataset-table">
                    <thead><tr><th>OS</th><th>Applications</th><th>Fraud</th><th>Rate</th></tr></thead>
                    <tbody>{data.account.by_device_os.map(row => (
                      <tr key={row.device_os}>
                        <td>{row.device_os}</td><td>{formatNumber(row.count)}</td>
                        <td>{formatNumber(row.fraud_count)}</td>
                        <td>{formatNumber(row.fraud_rate * 100, 2)}%</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            </div>
            <p className="dataset-panel-note">
              Đây là thống kê mô tả theo source feature; chưa tạo risk label hoặc alert từ ngưỡng chưa hiệu chỉnh.
            </p>
          </>
        ) : <Empty>Chưa có dữ liệu BAF để phân tích account application.</Empty>}
      </section>

    </div>
  );
}
