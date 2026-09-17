import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Zap, Server } from 'lucide-react';
import OverviewTab from './components/OverviewTab';
import SecurityTab from './components/SecurityTab';
import AnalyticsTab from './components/AnalyticsTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [alerts, setAlerts] = useState([]);
  const [tps, setTps] = useState(0);
  const [targetTps, setTargetTps] = useState(2);
  const [totalValue, setTotalValue] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  
  // Real-time chart data
  const [chartData, setChartData] = useState(() => {
    return Array.from({ length: 20 }, (_, i) => ({
      time: new Date(Date.now() - (20 - i) * 1000).toLocaleTimeString([], { hour12: false }),
      amount: 0
    }));
  });

  const [mapData, setMapData] = useState([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/stream");

    ws.onopen = () => {
      console.log("Connected to WebSocket");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
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

        // Update Heatmap
        if (message.data.lat && message.data.lng) {
          setMapData(prev => {
            const newMap = [...prev, { lat: message.data.lat, lng: message.data.lng }];
            if (newMap.length > 50) newMap.shift();
            return newMap;
          });
        }

      } else if (message.topic === "fraud-events" || message.topic === "aml-events") {
        setAlerts(prev => {
          const newAlerts = [message.data, ...prev];
          if (newAlerts.length > 5) newAlerts.pop();
          return newAlerts;
        });
      }
    };

    ws.onclose = () => setIsConnected(false);

    // Reset TPS counter every second
    const interval = setInterval(() => {
      setTps(0);
    }, 1000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, []);

  const donutData = [
    { name: 'Velocity (Redis)', value: 45, color: '#ef4444' },
    { name: 'Structuring (AML)', value: 30, color: '#f59e0b' },
    { name: 'Large Amount', value: 25, color: '#3b82f6' },
  ];

  const graphData = {
    nodes: [
      { id: 'ACC_1', group: 1 }, { id: 'ACC_2', group: 1 }, { id: 'ACC_3', group: 1 },
      { id: 'ACC_4', group: 2 }, { id: 'ACC_5', group: 2 }, { id: 'ACC_6', group: 2 },
      { id: 'MERCHANT_X', group: 3 }
    ],
    links: [
      { source: 'ACC_1', target: 'ACC_2', value: 1 },
      { source: 'ACC_2', target: 'ACC_3', value: 1 },
      { source: 'ACC_3', target: 'ACC_1', value: 1 },
      { source: 'ACC_4', target: 'MERCHANT_X', value: 1 },
      { source: 'ACC_5', target: 'MERCHANT_X', value: 1 },
      { source: 'ACC_6', target: 'MERCHANT_X', value: 1 }
    ]
  };

  const scatterData = Array.from({length: 40}, (_, i) => {
    const isAnomaly = Math.random() > 0.9;
    return {
      x: Date.now() - (40 - i) * 60000,
      y: isAnomaly ? Math.random() * 8000 + 5000 : Math.random() * 1000,
      isAnomaly
    }
  });

  const riskyAccountsData = [
    { name: 'ACC_92', score: 98 },
    { name: 'ACC_11', score: 92 },
    { name: 'ACC_44', score: 87 },
    { name: 'ACC_05', score: 81 },
    { name: 'ACC_73', score: 76 }
  ];

  const sankeyData = {
    nodes: [{ name: 'Bank A' }, { name: 'Bank B' }, { name: 'Crypto Ex' }, { name: 'Offshore' }],
    links: [
      { source: 0, target: 1, value: 50000 },
      { source: 1, target: 2, value: 35000 },
      { source: 1, target: 3, value: 15000 },
      { source: 2, target: 3, value: 20000 }
    ]
  };

  const funnelData = [
    { name: 'Total TX', value: 10000, fill: '#3b82f6' },
    { name: 'DQ Passed', value: 9800, fill: '#10b981' },
    { name: 'Fraud Checked', value: 9500, fill: '#f59e0b' },
    { name: 'Cleared', value: 9400, fill: '#ef4444' }
  ];

  return (
    <div className="dashboard-container">
      <header className="header">
        <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
          <Activity className="icon pulse" size={28} />
          <h1>Unified Command Center</h1>
        </div>
        
        <div style={{display: 'flex', alignItems: 'center', gap: '2rem'}}>
          {/* TPS Control Slider */}
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem 1rem', borderRadius: '8px'}}>
            <span style={{fontSize: '0.875rem', color: 'var(--text-secondary)'}}>Mock TPS ({targetTps}):</span>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={targetTps}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                setTargetTps(val);
                fetch('http://localhost:8000/api/config/tps', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({tps: val})
                }).catch(err => console.error("Error setting TPS:", err));
              }}
              style={{cursor: 'pointer', accentColor: 'var(--accent-color)'}}
            />
          </div>

          <div className="status-badge" style={{borderColor: isConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}}>
            <span className="dot" style={{backgroundColor: isConnected ? '#10b981' : '#ef4444'}}></span>
            {isConnected ? 'LIVE (Kafka Connected)' : 'DISCONNECTED'}
          </div>
        </div>
      </header>

      {/* Tabs Navigation */}
      <div className="tabs">
        <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          🌐 Overview & Real-time
        </button>
        <button className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`} onClick={() => setActiveTab('security')}>
          🛡️ Security & AML
        </button>
        <button className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
          📈 Analytics & Governance
        </button>
      </div>

      <main>
        {/* Metric Cards (Always visible) */}
        <div className="grid" style={{marginBottom: '1.5rem'}}>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Activity className="icon" size={20} />
              <span>TPS / Lưu lượng</span>
            </div>
            <div className="metric-value">{tps} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>tx/s</span></div>
          </div>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Zap className="icon" size={20} style={{color: '#10b981'}} />
              <span>Giá trị lưu chuyển (24h)</span>
            </div>
            <div className="metric-value">${totalValue.toLocaleString()}</div>
          </div>
          <div className="metric-card col-span-4">
            <div className="metric-header">
              <Server className="icon" size={20} style={{color: '#8b5cf6'}} />
              <span>System Health</span>
            </div>
            <div className="metric-value" style={{color: '#10b981'}}>99.9%</div>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && <OverviewTab data={chartData} mapData={mapData} />}
        {activeTab === 'security' && <SecurityTab alerts={alerts} graphData={graphData} scatterData={scatterData} riskyAccountsData={riskyAccountsData} donutData={donutData} />}
        {activeTab === 'analytics' && <AnalyticsTab sankeyData={sankeyData} funnelData={funnelData} />}
      </main>
    </div>
  );
}
