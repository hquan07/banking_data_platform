import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import { Users, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
const SEVERITY_COLORS = { high: '#ef4444', medium: '#f59e0b', low: '#3b82f6' };

export default function UserManagementTab() {
  const [usersStats, setUsersStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/admin/users-stats', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        if (!res.ok) {
          throw new Error('Failed to fetch user stats. Are you an Admin?');
        }
        const data = await res.json();
        setUsersStats(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) return <div style={{padding: '2rem', color: '#fff'}}>Loading user statistics...</div>;
  if (error) return <div style={{padding: '2rem', color: '#ef4444'}}>Error: {error}</div>;

  // Process data for charts
  const performanceData = usersStats.map(u => ({
    name: u.username,
    Resolved: u.total_resolved,
    Pending: u.pending
  }));

  const workloadData = usersStats.map(u => ({
    name: u.username,
    value: u.total_assigned
  })).filter(d => d.value > 0);

  const severityData = usersStats.map(u => ({
    name: u.username,
    High: u.severity.high,
    Medium: u.severity.medium,
    Low: u.severity.low
  }));

  // Find all unique rules for Radar chart
  const allRules = new Set();
  usersStats.forEach(u => {
    Object.keys(u.rules || {}).forEach(r => allRules.add(r));
  });
  
  const radarData = Array.from(allRules).map(rule => {
    const dataPoint = { subject: rule };
    usersStats.forEach(u => {
      dataPoint[u.username] = u.rules[rule] || 0;
    });
    return dataPoint;
  });

  return (
    <div style={{ padding: '20px', color: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px', gap: '10px' }}>
        <Users size={24} color="#8b5cf6" />
        <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>Admin User Management & KPIs</h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        
        {/* 1. Performance Chart (Grouped Bar) */}
        <div className="panel">
          <h3>Investigator Performance (Resolved vs Pending)</h3>
          <div style={{ height: '300px', marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend />
                <Bar dataKey="Resolved" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Pending" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Severity Breakdown (Stacked Bar) */}
        <div className="panel">
          <h3>Severity Workload Breakdown</h3>
          <div style={{ height: '300px', marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend />
                <Bar dataKey="High" stackId="a" fill={SEVERITY_COLORS.high} />
                <Bar dataKey="Medium" stackId="a" fill={SEVERITY_COLORS.medium} />
                <Bar dataKey="Low" stackId="a" fill={SEVERITY_COLORS.low} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Workload Distribution (Donut) */}
        <div className="panel">
          <h3>Workload Distribution (Total Assigned)</h3>
          <div style={{ height: '300px', marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={workloadData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={5}
                  dataKey="value"
                  label={({name, percent}) => `${name} (${(percent * 100).toFixed(0)}%)`}
                >
                  {workloadData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Rule Expertise (Radar) */}
        <div className="panel">
          <h3>Rule Expertise & Specialization</h3>
          <div style={{ height: '300px', marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <PolarRadiusAxis stroke="#334155" />
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend />
                {usersStats.map((u, index) => (
                  <Radar key={u.username} name={u.username} dataKey={u.username} stroke={COLORS[index % COLORS.length]} fill={COLORS[index % COLORS.length]} fillOpacity={0.4} />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="panel" style={{ overflowX: 'auto' }}>
        <h3>User Statistics Details</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>ID</th>
              <th style={{ padding: '12px' }}>Username</th>
              <th style={{ padding: '12px' }}>Role</th>
              <th style={{ padding: '12px' }}>Total Assigned</th>
              <th style={{ padding: '12px' }}>Resolved</th>
              <th style={{ padding: '12px' }}>Pending</th>
              <th style={{ padding: '12px' }}>Avg Risk Score</th>
            </tr>
          </thead>
          <tbody>
            {usersStats.map((u) => (
              <tr key={u.id} style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px' }}>{u.id}</td>
                <td style={{ padding: '12px', fontWeight: 'bold' }}>{u.username}</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ 
                    background: u.role === 'ADMIN' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(59, 130, 246, 0.2)', 
                    color: u.role === 'ADMIN' ? '#c4b5fd' : '#93c5fd',
                    padding: '4px 8px', borderRadius: '12px', fontSize: '0.75rem' 
                  }}>
                    {u.role}
                  </span>
                </td>
                <td style={{ padding: '12px' }}>{u.total_assigned}</td>
                <td style={{ padding: '12px', color: '#10b981' }}>{u.total_resolved}</td>
                <td style={{ padding: '12px', color: '#f59e0b' }}>{u.pending}</td>
                <td style={{ padding: '12px', color: u.avg_risk > 80 ? '#ef4444' : (u.avg_risk > 50 ? '#f59e0b' : '#10b981') }}>
                  {u.avg_risk}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
