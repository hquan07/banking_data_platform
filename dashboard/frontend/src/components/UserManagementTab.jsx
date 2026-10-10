import React, { useContext, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuthContext } from './AuthContext';
import { Badge, formatNumber, formatPercent, MetricCard, PageHeader, Panel, StateMessage } from './ui';

export default function UserManagementTab() {
  const { token } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/admin/users-stats', { headers:{ Authorization:`Bearer ${token}` }, signal:controller.signal })
      .then(async response => { if (!response.ok) throw new Error((await response.json()).detail || `Không tải được KPI (${response.status})`); return response.json(); })
      .then(data => setUsers(Array.isArray(data) ? data : []))
      .catch(fetchError => { if (fetchError.name !== 'AbortError') setError(fetchError.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token]);

  const totals = useMemo(() => users.reduce((acc, item) => ({ assigned:acc.assigned + item.total_assigned, resolved:acc.resolved + item.total_resolved, pending:acc.pending + item.pending, risk:acc.risk + Number(item.avg_risk || 0) }), { assigned:0, resolved:0, pending:0, risk:0 }), [users]);
  const lifecycle = users.map(item => ({ name:item.username, Resolved:item.total_resolved, Open:item.pending }));
  const severity = users.map(item => ({ name:item.username, High:item.severity.high, Medium:item.severity.medium, Low:item.severity.low }));

  return <div className="page-stack">
    <PageHeader eyebrow="Team operations" title="Investigator KPIs" description="Workload và case outcomes theo assignee; benchmark chưa được giao analyst vẫn được giữ ngoài KPI cá nhân." />
    <MetricCard icon={<Users size={17} />} label="Investigators" value={formatNumber(users.length)} detail="Bao gồm admin và analyst" tone="blue" />
    <MetricCard icon={<AlertTriangle size={17} />} label="Assigned cases" value={formatNumber(totals.assigned)} detail={`${formatNumber(totals.pending)} đang mở`} tone="amber" />
    <MetricCard icon={<CheckCircle2 size={17} />} label="Resolution rate" value={formatPercent(totals.assigned ? totals.resolved / totals.assigned : 0)} detail={`${formatNumber(totals.resolved)} case resolved`} tone="green" />
    <MetricCard icon={<Clock3 size={17} />} label="Average risk" value={formatNumber(users.length ? totals.risk / users.length : 0, 1)} detail="Trung bình theo investigator" tone="violet" />
    {loading ? <Panel className="col-span-12"><StateMessage type="loading">Đang tải investigator KPIs…</StateMessage></Panel> : error ? <Panel className="col-span-12"><StateMessage type="error">{error}</StateMessage></Panel> : <>
      <Panel className="col-span-6" title="Case lifecycle by investigator" subtitle="Resolved so với pending/investigating"><ResponsiveContainer width="100%" height={300}><BarChart data={lifecycle}><CartesianGrid stroke="#20314b" vertical={false}/><XAxis dataKey="name" stroke="#70839e" fontSize={9}/><YAxis stroke="#70839e" fontSize={9} allowDecimals={false}/><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }}/><Legend/><Bar dataKey="Resolved" fill="#35d399" radius={[4,4,0,0]}/><Bar dataKey="Open" fill="#f7b84b" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></Panel>
      <Panel className="col-span-6" title="Severity workload" subtitle="Risk bands của case đã assign"><ResponsiveContainer width="100%" height={300}><BarChart data={severity}><CartesianGrid stroke="#20314b" vertical={false}/><XAxis dataKey="name" stroke="#70839e" fontSize={9}/><YAxis stroke="#70839e" fontSize={9} allowDecimals={false}/><Tooltip contentStyle={{ background:'#0d1829', border:'1px solid #263750', fontSize:10 }}/><Legend/><Bar dataKey="High" stackId="risk" fill="#fb7185"/><Bar dataKey="Medium" stackId="risk" fill="#f7b84b"/><Bar dataKey="Low" stackId="risk" fill="#4f8cff" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></Panel>
      <Panel className="col-span-12" title="Investigator detail" subtitle="Account role và case ownership hiện tại"><div className="dataset-table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Assigned</th><th>Resolved</th><th>Open</th><th>Average risk</th><th>Rule coverage</th></tr></thead><tbody>{users.map(item => <tr key={item.id}><td><strong>{item.username}</strong><small> ID {item.id}</small></td><td><Badge tone={item.role === 'ADMIN' ? 'violet' : 'blue'}>{item.role}</Badge></td><td>{formatNumber(item.total_assigned)}</td><td>{formatNumber(item.total_resolved)}</td><td>{formatNumber(item.pending)}</td><td>{formatNumber(item.avg_risk, 1)}</td><td>{formatNumber(Object.keys(item.rules || {}).length)}</td></tr>)}</tbody></table></div>{!users.length && <StateMessage>Chưa có user trong hệ thống.</StateMessage>}</Panel>
    </>}
  </div>;
}
