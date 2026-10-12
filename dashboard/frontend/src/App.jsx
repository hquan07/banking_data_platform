import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { BarChart3, Database, History, LayoutDashboard, LogOut, Network, Radio, Search, Settings, ShieldAlert, Users } from 'lucide-react';
import Login from './components/Login';
import { AuthContext, AuthProvider } from './components/AuthContext';
import DatasetContextBar from './components/DatasetContextBar';
import TabErrorBoundary from './components/TabErrorBoundary';
import { RuntimeStatus } from './components/ui';
import { DatasetProvider, useDatasetContext } from './components/DatasetContext';
import { fixedDatasetForTab } from './datasetContextContract';
import { formatDataAge, humanizeRuntimeReason } from './runtimeStatus';
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
  const linked = new URLSearchParams(window.location.search).get('tab');
  if ([...WORKSPACE_TABS, ...ADMIN_TABS].includes(linked)) return linked;
  const stored = sessionStorage.getItem('sentinel-active-tab');
  return [...WORKSPACE_TABS, ...ADMIN_TABS].includes(stored) ? stored : 'overview';
}

function NavButton({ id, active, onSelect, icon, children, badge, disabled = false, reason = null }) {
  return <button className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => onSelect(id)} disabled={disabled} title={reason || undefined} aria-label={disabled && reason ? `${children}: ${reason}` : undefined}>{icon}<span>{children}</span>{badge > 0 && <span className="badge">{badge}</span>}</button>;
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
  const liveLastSeen = useRef(0);
  const [lastLiveAt, setLastLiveAt] = useState(0);
  const [totalValue, setTotalValue] = useState(0);
  const [sessionEvents, setSessionEvents] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [chartData, setChartData] = useState([]);
  const { token, user, logout } = React.useContext(AuthContext);
  const {
    datasetId, setDatasetId, manifest, manifestLoading, manifestError,
    tabCapability: capabilityForTab,
  } = useDatasetContext();
  const fixedDatasetId = fixedDatasetForTab(activeTab, manifest);
  const navigationCapability = tabId => {
    const fixed = fixedDatasetForTab(tabId, manifest);
    return capabilityForTab(tabId, fixed || datasetId);
  };
  const selectTab = tab => {
    const tabDatasetId = fixedDatasetForTab(tab, manifest);
    if (tabDatasetId && tabDatasetId !== datasetId) setDatasetId(tabDatasetId);
    setActiveTab(tab);
    sessionStorage.setItem('sentinel-active-tab', tab);
    const params = new URLSearchParams(window.location.search);
    params.set('tab', tab);
    if (tab !== 'security') ['case', 'page', 'q', 'status', 'risk'].forEach(key => params.delete(key));
    if (tab !== 'analytics') ['account', 'event', 'run'].forEach(key => params.delete(key));
    const nextUrl = `${window.location.pathname}?${params.toString()}${window.location.hash}`;
    if (nextUrl !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.pushState({}, '', nextUrl);
    }
  };

  useEffect(() => {
    const restoreLinkedTab = () => {
      const linked = readActiveTab();
      setActiveTab(linked);
      sessionStorage.setItem('sentinel-active-tab', linked);
    };
    window.addEventListener('popstate', restoreLinkedTab);
    return () => window.removeEventListener('popstate', restoreLinkedTab);
  }, []);

  useEffect(() => {
    if (user?.role !== 'ADMIN' && ADMIN_TABS.includes(activeTab)) selectTab('overview');
  }, [activeTab, user?.role]);

  useEffect(() => {
    if (fixedDatasetId && fixedDatasetId !== datasetId) setDatasetId(fixedDatasetId);
  }, [activeTab, datasetId, fixedDatasetId]);

  useEffect(() => {
    if (!WORKSPACE_TABS.includes(activeTab) || manifestLoading) return;
    const targetDataset = fixedDatasetId || datasetId;
    if (!capabilityForTab(activeTab, targetDataset).available) selectTab('datasets');
  }, [activeTab, datasetId, fixedDatasetId, manifest, manifestLoading]);

  useEffect(() => {
    let mounted = true;
    if (!token) return undefined;
    const ws = new WebSocket(`${window._env_?.WS_URL || 'ws://localhost:8000'}/ws/stream`, ['bearer', token]);
    ws.onopen = () => { if (mounted) setIsConnected(true); };
    ws.onmessage = event => {
      const message = parseStreamMessage(event.data);
      if (!message) return;
      if (message.topic === 'payment-events') {
        liveLastSeen.current = Date.now();
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
      setLastLiveAt(liveLastSeen.current);
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
    lastLiveAt,
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
        <NavButton id="overview" active={activeTab} onSelect={selectTab} icon={<LayoutDashboard size={19} />} disabled={!navigationCapability('overview').available} reason={navigationCapability('overview').reason}>Command Center</NavButton>
        <NavButton id="fraud" active={activeTab} onSelect={selectTab} icon={<BarChart3 size={19} />} disabled={!navigationCapability('fraud').available} reason={navigationCapability('fraud').reason}>Fraud Monitor</NavButton>
        <NavButton id="security" active={activeTab} onSelect={selectTab} icon={<Search size={19} />} badge={alerts.length} disabled={!navigationCapability('security').available} reason={navigationCapability('security').reason}>Investigations</NavButton>
        <NavButton id="analytics" active={activeTab} onSelect={selectTab} icon={<Network size={19} />} disabled={!navigationCapability('analytics').available} reason={navigationCapability('analytics').reason}>AML Network</NavButton>
        <NavButton id="datasets" active={activeTab} onSelect={selectTab} icon={<Database size={19} />} disabled={!navigationCapability('datasets').available} reason={navigationCapability('datasets').reason}>Data Sources</NavButton>
        <NavButton id="history" active={activeTab} onSelect={selectTab} icon={<History size={19} />} disabled={!navigationCapability('history').available} reason={navigationCapability('history').reason}>Historical Analytics</NavButton>
      </div>
      {user?.role === 'ADMIN' && <><div className="nav-section-label nav-admin-label">Administration</div><div className="nav-menu">
        <NavButton id="users" active={activeTab} onSelect={selectTab} icon={<Users size={19} />}>Investigator KPIs</NavButton>
        <NavButton id="rules" active={activeTab} onSelect={selectTab} icon={<Settings size={19} />}>Detection Rules</NavButton>
        <NavButton id="architecture" active={activeTab} onSelect={selectTab} icon={<Network size={19} />}>Architecture Map</NavButton>
      </div></>}
    </nav>
    <div className="main-content">
      <header className="header">
        <div className="status-indicators" aria-live="polite"><RuntimeStatus status={streamStatus.state} compact /><span>{streamStatus.connection}</span><span className="header-divider" /><Radio size={15} /><span>{streamStatus.activity}</span><span className="header-stream-meta">Last event {streamStatus.lastSuccessAt ? new Date(streamStatus.lastSuccessAt).toLocaleTimeString('vi-VN') : 'not observed'} · {formatDataAge(streamStatus.ageSeconds)}{streamStatus.reason ? ` · ${humanizeRuntimeReason(streamStatus.reason)}` : ''}</span></div>
        <div className="user-profile"><span className="user-avatar">{user?.username?.slice(0, 2).toUpperCase()}</span><div><strong>{user?.username}</strong><small>{user?.role}</small></div><button className="icon-button" onClick={logout} aria-label="Đăng xuất"><LogOut size={17} /></button></div>
      </header>
      {!fixedDatasetId && <DatasetContextBar />}
      <main className="dashboard-container">{manifestError && <div className="capability-boundary capability-warning" role="alert">{manifestError}. Đang dùng capability fallback an toàn.</div>}<TabErrorBoundary key={`${activeTab}:${datasetId}`}><Suspense fallback={<div className="state-message">Đang tải nội dung…</div>}>
        {manifestLoading ? <div className="capability-boundary" role="status">Đang xác minh dashboard capabilities…</div> : fixedDatasetId && fixedDatasetId !== datasetId ? <div className="state-message">Đang áp dụng phạm vi DS3…</div> : <>
          {activeTab === 'overview' && <CommandCenterTab data={chartData} tps={liveTps} totalValue={totalValue} sessionEvents={sessionEvents} isConnected={isConnected} />}
          {activeTab === 'fraud' && <FraudMonitoringTab />}
          {activeTab === 'security' && <SecurityTab />}
          {activeTab === 'analytics' && <AnalyticsTab />}
          {activeTab === 'datasets' && <DatasetsTab />}
          {activeTab === 'history' && <HistoryTab />}
          {activeTab === 'users' && <UserManagementTab />}
          {activeTab === 'rules' && <RulesManagementTab />}
          {activeTab === 'architecture' && <ArchitectureTab />}
        </>}
      </Suspense></TabErrorBoundary></main>
    </div>
  </div>;
}

export default function App() { return <AuthProvider><DatasetProvider><MainApp /></DatasetProvider></AuthProvider>; }
