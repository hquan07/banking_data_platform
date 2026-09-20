import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from './AuthContext';
import { PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, ReferenceArea, Legend } from 'recharts';
import ForceGraph2D from 'react-force-graph-2d';
import { ShieldAlert } from 'lucide-react';

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6'];

export default function SecurityTab({ alerts, graphData, scatterData, riskyAccountsData, donutData }) {
  const { token } = useContext(AuthContext);
  const [pgAlerts, setPgAlerts] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = () => {
    if (!token) return;
    fetch('http://localhost:8000/api/alerts', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setPgAlerts(data);
      })
      .catch(console.error);
  };

  const handleUpdateStatus = (id, status) => {
    fetch(`http://localhost:8000/api/alerts/${id}/status`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ status })
    }).then(() => fetchAlerts()).catch(console.error);
  };

  const handleExportCSV = () => {
    fetch('http://localhost:8000/api/alerts/export', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => {
      if (!res.ok) throw new Error("You do not have permission to export.");
      return res.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'alerts_export.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    })
    .catch(err => alert("Error exporting CSV: " + err.message));
  };

  const totalPages = Math.max(1, Math.ceil(pgAlerts.length / itemsPerPage));
  const currentAlerts = pgAlerts.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="grid">
      {/* Alert Feed (Case Management) */}
      <div className="panel col-span-12">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <h2 className="panel-title" style={{margin: 0}}>Case Management (Postgres)</h2>
          <button onClick={handleExportCSV} style={{background: '#10b981', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold'}}>
            Export CSV
          </button>
        </div>
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
              {currentAlerts.map(alert => (
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
        {/* Pagination Controls */}
        {pgAlerts.length > 0 && (
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)'}}>
            <span style={{color: '#94a3b8', fontSize: '0.875rem'}}>
              Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, pgAlerts.length)} of {pgAlerts.length} entries
            </span>
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                style={{background: currentPage === 1 ? 'rgba(255,255,255,0.05)' : 'rgba(59, 130, 246, 0.1)', color: currentPage === 1 ? '#64748b' : '#3b82f6', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer'}}
              >
                Previous
              </button>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                <span style={{color: '#fff', padding: '0 8px'}}>{currentPage} / {totalPages}</span>
              </div>
              <button 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                style={{background: currentPage === totalPages ? 'rgba(255,255,255,0.05)' : 'rgba(59, 130, 246, 0.1)', color: currentPage === totalPages ? '#64748b' : '#3b82f6', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'}}
              >
                Next
              </button>
            </div>
          </div>
        )}
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
            <XAxis dataKey="x" type="number" name="Time" stroke="rgba(255,255,255,0.5)" domain={['dataMin', 'dataMax']} tickFormatter={(unixTime) => new Date(unixTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} />
            <YAxis dataKey="y" type="number" name="Amount ($)" stroke="rgba(255,255,255,0.5)" tickFormatter={(val) => `$${val}`} />
            <ZAxis dataKey="z" type="number" range={[50, 400]} />
            
            <ReferenceArea y1={5000} fill="rgba(239, 68, 68, 0.05)" strokeOpacity={0.3} ifOverflow="hidden" />
            
            <RechartsTooltip 
              cursor={{ strokeDasharray: '3 3' }} 
              contentStyle={{backgroundColor: '#141a28', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div style={{ background: '#141a28', padding: '12px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                      <p style={{ margin: '0 0 8px 0', color: '#94a3b8', fontSize: '12px' }}>{new Date(data.x).toLocaleTimeString()}</p>
                      <p style={{ margin: '0 0 4px 0', color: data.isAnomaly ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>
                        Amount: ${data.y.toFixed(2)}
                      </p>
                      <p style={{ margin: '0', color: '#fff', fontSize: '13px' }}>
                        Status: <span style={{color: data.isAnomaly ? '#ef4444' : '#94a3b8'}}>{data.reason}</span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend verticalAlign="top" height={36} content={() => (
              <div style={{display: 'flex', justifyContent: 'center', gap: '20px', color: '#94a3b8', fontSize: '14px', marginBottom: '10px'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#3b82f6'}}></div> Normal Transaction
                </div>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444'}}></div> High Risk / Anomaly
                </div>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <div style={{width: '24px', height: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px dashed rgba(239, 68, 68, 0.3)'}}></div> Anomaly Threshold (&gt;$5,000)
                </div>
              </div>
            )} />
            <Scatter name="Transactions" data={scatterData} fill="#3b82f6">
              {scatterData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.isAnomaly ? '#ef4444' : '#3b82f6'} opacity={0.8} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
