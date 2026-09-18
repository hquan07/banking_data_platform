import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import ForceGraph2D from 'react-force-graph-2d';
import { ShieldAlert } from 'lucide-react';

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6'];

export default function SecurityTab({ alerts, graphData, scatterData, riskyAccountsData, donutData }) {
  const [pgAlerts, setPgAlerts] = useState([]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = () => {
    fetch('http://localhost:8000/api/alerts')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setPgAlerts(data);
      })
      .catch(console.error);
  };

  const handleUpdateStatus = (id, status) => {
    fetch(`http://localhost:8000/api/alerts/${id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).then(() => fetchAlerts()).catch(console.error);
  };

  return (
    <div className="grid">
      {/* Alert Feed (Case Management) */}
      <div className="panel col-span-12">
        <h2 className="panel-title">Case Management (Postgres)</h2>
        <div style={{overflowX: 'auto'}}>
          <table style={{width: '100%', textAlign: 'left', borderCollapse: 'collapse', marginTop: '1rem'}}>
            <thead>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8'}}>
                <th style={{padding: '8px'}}>ID</th>
                <th style={{padding: '8px'}}>Time</th>
                <th style={{padding: '8px'}}>Account</th>
                <th style={{padding: '8px'}}>Rule</th>
                <th style={{padding: '8px'}}>Risk</th>
                <th style={{padding: '8px'}}>Status</th>
                <th style={{padding: '8px'}}>Action</th>
              </tr>
            </thead>
            <tbody>
              {pgAlerts.map(alert => (
                <tr key={alert.alert_id} style={{borderBottom: '1px solid rgba(255,255,255,0.05)'}}>
                  <td style={{padding: '12px 8px'}}>#{alert.alert_id}</td>
                  <td style={{padding: '12px 8px'}}>{new Date(alert.created_at).toLocaleTimeString()}</td>
                  <td style={{padding: '12px 8px', fontWeight: 'bold'}}>{alert.account_id}</td>
                  <td style={{padding: '12px 8px', color: '#f59e0b'}}>{alert.rule_name}</td>
                  <td style={{padding: '12px 8px'}}>
                    <span style={{padding: '2px 8px', borderRadius: '12px', background: alert.risk_score > 90 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)', color: alert.risk_score > 90 ? '#ef4444' : '#f59e0b'}}>
                      {alert.risk_score}
                    </span>
                  </td>
                  <td style={{padding: '12px 8px'}}>
                    <span style={{color: alert.status === 'RESOLVED' ? '#10b981' : alert.status === 'IGNORED' ? '#94a3b8' : '#3b82f6'}}>
                      {alert.status}
                    </span>
                  </td>
                  <td style={{padding: '12px 8px'}}>
                    {alert.status === 'PENDING' && (
                      <div style={{display: 'flex', gap: '8px'}}>
                        <button 
                          onClick={() => handleUpdateStatus(alert.alert_id, 'RESOLVED')}
                          style={{background: '#10b981', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px'}}
                        >
                          Resolve
                        </button>
                        <button 
                          onClick={() => handleUpdateStatus(alert.alert_id, 'IGNORED')}
                          style={{background: '#64748b', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px'}}
                        >
                          Ignore
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {pgAlerts.length === 0 && (
                <tr><td colSpan="7" style={{textAlign: 'center', padding: '20px', color: '#64748b'}}>No alerts in Postgres database</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fraud Distribution */}
      <div className="panel col-span-6">
        <h2 className="panel-title">Fraud Distribution</h2>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={donutData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
              {donutData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <RechartsTooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Top Risky Accounts */}
      <div className="panel col-span-6">
        <h2 className="panel-title">Top Risky Accounts</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={riskyAccountsData} layout="vertical" margin={{top: 5, right: 30, left: 20, bottom: 5}}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
            <XAxis type="number" stroke="rgba(255,255,255,0.5)" />
            <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.5)" width={80} />
            <RechartsTooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
              cursor={{fill: 'rgba(255,255,255,0.05)'}}
            />
            <Bar dataKey="score" fill="#ef4444" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Anomaly Scatter Plot */}
      <div className="panel col-span-12" style={{height: '350px'}}>
        <h2 className="panel-title">Anomaly Detection (Scatter Plot)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="x" type="number" name="Time" stroke="rgba(255,255,255,0.5)" domain={['dataMin', 'dataMax']} tick={false} />
            <YAxis dataKey="y" type="number" name="Amount" stroke="rgba(255,255,255,0.5)" />
            <RechartsTooltip 
              cursor={{ strokeDasharray: '3 3' }} 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
            <Scatter name="Transactions" data={scatterData} fill="#3b82f6">
              {scatterData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.isAnomaly ? '#ef4444' : '#3b82f6'} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
