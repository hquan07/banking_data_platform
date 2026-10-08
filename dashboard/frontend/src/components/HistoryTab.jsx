import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

export default function HistoryTab() {
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/analytics/history')
      .then(async res => { if (!res.ok) throw new Error('Không tải được dữ liệu lịch sử'); return res.json(); })
      .then(data => {
        if (!Array.isArray(data)) throw new Error('Định dạng dữ liệu lịch sử không hợp lệ');
        // Map date to string if needed, format the data
        const formattedData = data.map(item => ({
          ...item,
          total_tx: Number(item.total_tx),
          total_fraud: Number(item.total_fraud),
          total_amount: Number(item.total_amount)
        }));
        setHistoryData(formattedData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px', color: '#94a3b8'}}>Loading ClickHouse Historical Data...</div>;
  }
  if (error) return <div role="alert" style={{color: '#ef4444'}}>{error}</div>;
  if (historyData.length === 0) return <div role="status" style={{color: '#94a3b8'}}>Chưa có giao dịch lịch sử.</div>;

  return (
    <div className="grid">
      <div className="panel col-span-12" style={{height: '400px'}}>
        <h2 className="panel-title">Transaction Volume (30 Days) - ClickHouse</h2>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={historyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#94a3b8" />
            <YAxis yAxisId="left" orientation="left" stroke="#94a3b8" />
            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" />
            <Tooltip 
              contentStyle={{backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px'}} 
              itemStyle={{color: '#f8fafc'}}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="total_tx" name="Total Transactions" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar yAxisId="right" dataKey="total_fraud" name="Alerts created (all statuses)" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel col-span-12" style={{height: '400px'}}>
        <h2 className="panel-title">Total Transaction Value (USD) - ClickHouse</h2>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={historyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip 
              contentStyle={{backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px'}} 
              itemStyle={{color: '#f8fafc'}}
            />
            <Legend />
            <Line type="monotone" dataKey="total_amount" name="Total Amount ($)" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
