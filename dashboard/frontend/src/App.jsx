import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { BarChart3, Database, History, LayoutDashboard, LogOut, Network, Radio, Search, Settings, ShieldAlert, Users } from 'lucide-react';
import Login from './components/Login';
import { AuthContext, AuthProvider } from './components/AuthContext';
import DatasetContextBar from './components/DatasetContextBar';
import { DatasetProvider, useDatasetContext } from './components/DatasetContext';
import { describeStreamStatus, parseStreamMessage } from './streamContract';
import './index.css';

const CommandCenterTab = lazy(() => import('./components/CommandCenterTab'));
const FraudMonitoringTab = lazy(() => import('./components/FraudMonitoringTab'));
const SecurityTab = lazy(() => import('./components/SecurityTab'));
const AnalyticsTab = lazy(() => import('./components/AnalyticsTab'));
const DatasetsTab = lazy(() => import('./components/DatasetsTab'));
const HistoryTab = lazy(() => import('./components/HistoryTab'));
const UserManagementTab = lazy(() => import('./components/UserManagementTab'));
const RulesManagementTab = lazy(() => import('./components/RulesManagementTab'));
const ArchitectureTab = lazy(() => import('./components/ArchitectureTab'));
const WORKSPACE_TABS = ['overview', 'fraud', 'security', 'analytics', 'datasets', 'history'];
const ADMIN_TABS = ['users', 'rules', 'architecture'];

function readActiveTab() {
  const stored = sessionStorage.getItem('sentinel-active-tab');
  return [...WORKSPACE_TABS, ...ADMIN_TABS].includes(stored) ? stored : 'overview';
}

function NavButton({ id, active, onSelect, icon, children, badge }) {
  return <button className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => onSelect(id)}>{icon}<span>{children}</span>{badge > 0 && <span className="badge">{badge}</span>}</button>;
}

function MainApp() {
  const [activeTab, setActiveTab] = useState(readActiveTab);
  const [alerts, setAlerts] = useState([]);
  const [liveTps, setLiveTps] = useState(0);
  const [benchmarkTps, setBenchmarkTps] = useState({});
  const [lastBenchmarkAt, setLastBenchmarkAt] = useState({});
  const [streamClock, setStreamClock] = useState(Date.now());
  const liveEventsThisSecond = useRef(0);
  const benchmarkEventsThisSecond = useRef({});
  const benchmarkLastSeen = useRef({});
  const [totalValue, setTotalValue] = useState(0);
  const [sessionEvents, setSessionEvents] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [chartData, setChartData] = useState([]);
  const { token, user, logout } = React.useContext(AuthContext);
  const { datasetId } = useDatasetContext();
  const selectTab = tab => { setActiveTab(tab); sessionStorage.setItem('sentinel-active-tab', tab); };

  useEffect(() => {
    if (user?.role !== 'ADMIN' && ADMIN_TABS.includes(activeTab)) selectTab('overview');
  }, [activeTab, user?.role]);

  useEffect(() => {
    let mounted = true;
    if (!token) return undefined;
    const ws = new WebSocket(`${window._env_?.WS_URL || 'ws://localhost:8000'}/ws/stream`, ['bearer', token]);
    ws.onopen = () => { if (mounted) setIsConnected(true); };
    ws.onmessage = event => {
      const message = parseStreamMessage(event.data);
      if (!message) return;
      if (message.topic === 'payment-events') {
        liveEventsThisSecond.current += 1;
        setSessionEvents(value => value + 1);
        setTotalValue(value => value + message.data.amount);
        setChartData(previous => [...previous.slice(-59), { time: new Date().toLocaleTimeString('vi-VN', { hour12: false }), amount: message.data.amount }]);
      } else if (message.topic === 'benchmark-events') {
        const benchmarkDatasetId = message.data.dataset_id;
        const receivedAt = Date.now();
        benchmarkEventsThisSecond.current[benchmarkDatasetId] = (benchmarkEventsThisSecond.current[benchmarkDatasetId] || 0) + 1;
        benchmarkLastSeen.current[benchmarkDatasetId] = receivedAt;
      } else {
        setAlerts(previous => [message.data, ...previous].slice(0, 20));
      }
    };
    ws.onclose = () => { if (mounted) setIsConnected(false); };
    const interval = window.setInterval(() => {
      setLiveTps(liveEventsThisSecond.current);
      setBenchmarkTps({ ...benchmarkEventsThisSecond.current });
      setLastBenchmarkAt({ ...benchmarkLastSeen.current });
      liveEventsThisSecond.current = 0;
      benchmarkEventsThisSecond.current = {};
      setStreamClock(Date.now());
    }, 1000);
    return () => { mounted = false; ws.close(); window.clearInterval(interval); };
  }, [token]);

  const streamStatus = describeStreamStatus({
    datasetId,
    isConnected,
    liveRate: liveTps,
    benchmarkRate: benchmarkTps[datasetId] || 0,
    lastBenchmarkAt: lastBenchmarkAt[datasetId] || 0,
    now: streamClock,
  });

  if (!token) return <Login />;

  return <div className="app-container">
    <nav className="sidebar" aria-label="Điều hướng chính">
      <div className="sidebar-logo"><span className="brand-mark"><ShieldAlert size={22} /></span><div><h1>Sentinel</h1><small>Banking Intelligence</small></div></div>
      <div className="nav-section-label">Workspace</div>
      <div className="nav-menu">
        <NavButton id="overview" active={activeTab} onSelect={selectTab} icon={<LayoutDashboard size={19} />}>Command Center</NavButton>
        <NavButton id="fraud" active={activeTab} onSelect={selectTab} icon={<BarChart3 size={19} />}>Fraud Monitor</NavButton>
        <NavButton id="security" active={activeTab} onSelect={selectTab} icon={<Search size={19} />} badge={alerts.length}>Investigations</NavButton>
        <NavButton id="analytics" active={activeTab} onSelect={selectTab} icon={<Network size={19} />}>AML Network</NavButton>
        <NavButton id="datasets" active={activeTab} onSelect={selectTab} icon={<Database size={19} />}>Data Sources</NavButton>
        <NavButton id="history" active={activeTab} onSelect={selectTab} icon={<History size={19} />}>Historical Analytics</NavButton>
      </div>
      {user?.role === 'ADMIN' && <><div className="nav-section-label nav-admin-label">Administration</div><div className="nav-menu">
        <NavButton id="users" active={activeTab} onSelect={selectTab} icon={<Users size={19} />}>Investigator KPIs</NavButton>
        <NavButton id="rules" active={activeTab} onSelect={selectTab} icon={<Settings size={19} />}>Detection Rules</NavButton>
        <NavButton id="architecture" active={activeTab} onSelect={selectTab} icon={<Network size={19} />}>Platform Health</NavButton>
      </div></>}
    </nav>
    <div className="main-content">
      <header className="header">
        <div className="status-indicators" aria-live="polite"><span className={`status-dot ${streamStatus.state === 'offline' ? 'disconnected' : streamStatus.state === 'idle' ? 'idle' : ''}`} /><span>{streamStatus.connection}</span><span className="header-divider" /><Radio size={15} /><span className={streamStatus.state === 'idle' ? 'stream-rate-idle' : ''}>{streamStatus.activity}</span></div>
        <div className="user-profile"><span className="user-avatar">{user?.username?.slice(0, 2).toUpperCase()}</span><div><strong>{user?.username}</strong><small>{user?.role}</small></div><button className="icon-button" onClick={logout} aria-label="Đăng xuất"><LogOut size={17} /></button></div>
      </header>
      <DatasetContextBar />
      <main className="dashboard-container"><Suspense fallback={<div className="state-message">Đang tải nội dung…</div>}>
        {activeTab === 'overview' && <CommandCenterTab data={chartData} tps={liveTps} totalValue={totalValue} sessionEvents={sessionEvents} isConnected={isConnected} />}
        {activeTab === 'fraud' && <FraudMonitoringTab />}
        {activeTab === 'security' && <SecurityTab />}
        {activeTab === 'analytics' && <AnalyticsTab />}
        {activeTab === 'datasets' && <DatasetsTab />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'users' && <UserManagementTab />}
        {activeTab === 'rules' && <RulesManagementTab />}
        {activeTab === 'architecture' && <ArchitectureTab />}
      </Suspense></main>
    </div>
  </div>;
}

export default function App() { return <AuthProvider><DatasetProvider><MainApp /></DatasetProvider></AuthProvider>; }
