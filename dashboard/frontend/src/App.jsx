import React, { Suspense, lazy, useState, useEffect } from 'react';
import { Activity, ShieldAlert, Zap, Server, LayoutDashboard, BarChart3, History, Settings, Users, Network } from 'lucide-react';
const OverviewTab = lazy(() => import('./components/OverviewTab'));
const SecurityTab = lazy(() => import('./components/SecurityTab'));
const AnalyticsTab = lazy(() => import('./components/AnalyticsTab'));
const HistoryTab = lazy(() => import('./components/HistoryTab'));
const RulesManagementTab = lazy(() => import('./components/RulesManagementTab'));
const UserManagementTab = lazy(() => import('./components/UserManagementTab'));
const ArchitectureTab = lazy(() => import('./components/ArchitectureTab'));
import Login from './components/Login';
import { parseStreamMessage } from './streamContract';
import { AuthProvider, AuthContext } from './components/AuthContext';
import './index.css';

function MainApp() {
  const [activeTab, setActiveTab] = useState('overview');
  const [alerts, setAlerts] = useState([]);
  const [tps, setTps] = useState(0);
  const [totalValue, setTotalValue] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const { token, user, logout } = React.useContext(AuthContext);
  
  // Real-time chart data
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    let isMounted = true;
    if (!token) return undefined;
    const ws = new WebSocket((window._env_?.WS_URL || "ws://localhost:8000") + "/ws/stream", ['bearer', token]);

    ws.onopen = () => {
      console.log("Connected to WebSocket");
      if (isMounted) setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = parseStreamMessage(event.data);
      if (!message) return;
      if (message.topic === "payment-events") {
        setTps(prev => prev + 1);
        setTotalValue(prev => prev + message.data.amount);
        
        // Update Area chart
        setChartData(prev => {
          const newData = [...prev.slice(1), {
            time: new Date().toLocaleTimeString([], { hour12: false }),
            amount: message.data.amount
          }];
          return newData;
        });

      } else if (message.topic === "fraud-events" || message.topic === "aml-events") {
        setAlerts(prev => {
          const newAlerts = [message.data, ...prev];
          if (newAlerts.length > 5) newAlerts.pop();
          return newAlerts;
        });
      }
    };

    ws.onclose = () => {
      if (isMounted) setIsConnected(false);
    };

    // Reset TPS counter every second
    const interval = setInterval(() => {
      setTps(0);
    }, 1000);

    return () => {
      isMounted = false;
      ws.close();
      clearInterval(interval);
    };
  }, [token]);

  if (!token) {
    return <Login />;
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="sidebar-logo">
          <ShieldAlert size={28} color="#3b82f6" />
          <h1>Command Center</h1>
        </div>
        <div className="nav-menu">
          <button className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
            <LayoutDashboard size={20} />
            Overview
          </button>
          <button className={`nav-item ${activeTab === 'security' ? 'active' : ''}`} onClick={() => setActiveTab('security')}>
            <ShieldAlert size={20} />
            Security 
            {alerts.length > 0 && <span className="badge">{alerts.length}</span>}
          </button>
          <button className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <BarChart3 size={20} />
            Analytics
          </button>
          <button className={`nav-item ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            <History size={20} />
            History
          </button>
          {user?.role === 'ADMIN' && (
            <>
              <button className={`nav-item ${activeTab === 'users' ? 'active' : ''}`} onClick={() => setActiveTab('users')}>
                <Users size={20} />
                Users
              </button>
              <button className={`nav-item ${activeTab === 'rules' ? 'active' : ''}`} onClick={() => setActiveTab('rules')}>
                <Settings size={20} />
                Rules
              </button>
              <button className={`nav-item ${activeTab === 'architecture' ? 'active' : ''}`} onClick={() => setActiveTab('architecture')}>
                <Network size={20} />
                Architecture Map
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Header */}
        <header className="header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div className="status-indicators">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span className="status-text">{isConnected ? 'WebSocket đã kết nối' : 'WebSocket chưa kết nối'}</span>
            <span style={{marginLeft: '20px', color: '#94a3b8'}}>Streaming TPS: <strong style={{color: '#fff'}}>{tps}</strong></span>
          </div>
          <div className="user-profile" style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
            <div style={{textAlign: 'right'}}>
              <div style={{fontWeight: 'bold', fontSize: '14px', color: '#fff'}}>{user?.username}</div>
              <div style={{fontSize: '12px', color: '#94a3b8'}}>{user?.role}</div>
            </div>
            <button onClick={logout} style={{background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px'}}>
              Logout
            </button>
          </div>
        </header>

        {/* Dynamic Tab Content */}
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '2rem', padding: '10px 20px'}}>
          <div className="status-badge" style={{borderColor: isConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}}>
            <span className="dot" style={{backgroundColor: isConnected ? '#10b981' : '#ef4444'}}></span>
            {isConnected ? 'Live stream' : 'Live stream disconnected'}
          </div>
        </div>
        <main className="dashboard-container">
          {/* Metric Cards (Always visible) */}
          <div className="grid" style={{marginBottom: '1.5rem'}}>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Activity className="icon" size={20} />
              <span>Lưu lượng WebSocket của phiên</span>
            </div>
            <div className="metric-value">{tps} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>tx/s</span></div>
          </div>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Zap className="icon" size={20} style={{color: '#10b981'}} />
              <span>Giá trị quan sát từ khi mở trang</span>
            </div>
            <div className="metric-value">${totalValue.toLocaleString()}</div>
          </div>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Server className="icon" size={20} style={{color: '#8b5cf6'}} />
              <span>Kết nối WebSocket</span>
            </div>
            <div className="metric-value" style={{color: isConnected ? '#10b981' : '#ef4444'}}>{isConnected ? 'Đã kết nối' : 'Mất kết nối'}</div>
          </div>
        </div>

        {/* Tab Content */}
        <Suspense fallback={<div role="status">Đang tải nội dung...</div>}>
        {activeTab === 'overview' && <OverviewTab data={chartData} />}
        {activeTab === 'security' && <SecurityTab />}
        {activeTab === 'analytics' && <AnalyticsTab />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'users' && <UserManagementTab />}
        {activeTab === 'rules' && <RulesManagementTab />}
        {activeTab === 'architecture' && <ArchitectureTab />}
        </Suspense>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
