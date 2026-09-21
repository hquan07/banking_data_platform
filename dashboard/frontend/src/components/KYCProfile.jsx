import React, { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext } from './AuthContext';
import ForceGraph2D from 'react-force-graph-2d';
import { X, Shield, Smartphone, Globe, TrendingUp, AlertTriangle } from 'lucide-react';

export default function KYCProfile({ accountId, onClose }) {
  const { token } = useContext(AuthContext);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const graphRef = useRef(null);

  useEffect(() => {
    if (!accountId || !token) return;
    setLoading(true);
    fetch(`http://localhost:8000/api/accounts/${accountId}/kyc`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [accountId, token]);

  if (!accountId) return null;

  const trustColor = (score) => {
    if (score >= 70) return '#10b981';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: '#0f1729', border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '16px', width: '90%', maxWidth: '1100px', maxHeight: '85vh',
        overflow: 'auto', padding: '2rem', position: 'relative',
      }} onClick={e => e.stopPropagation()}>
        {/* Close button */}
        <button onClick={onClose} style={{
          position: 'absolute', top: '16px', right: '16px',
          background: 'rgba(255,255,255,0.05)', border: 'none',
          borderRadius: '8px', padding: '8px', cursor: 'pointer', color: '#94a3b8',
        }}>
          <X size={20} />
        </button>

        {/* Header */}
        <div style={{marginBottom: '1.5rem'}}>
          <h2 style={{margin: '0 0 4px 0', color: '#fff', fontSize: '1.5rem'}}>
            KYC 360° — {accountId}
          </h2>
          <p style={{margin: 0, color: '#94a3b8', fontSize: '14px'}}>Hồ sơ khách hàng toàn diện</p>
        </div>

        {loading ? (
          <div style={{textAlign: 'center', padding: '60px', color: '#94a3b8'}}>
            Đang tải hồ sơ khách hàng...
          </div>
        ) : profile ? (
          <>
            {/* Top metrics row */}
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem'}}>
              {/* Trust Score */}
              <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px', marginBottom: '8px'}}>
                  <Shield size={16} /> Điểm Uy Tín
                </div>
                <div style={{fontSize: '2rem', fontWeight: 'bold', color: trustColor(profile.trust_score)}}>
                  {profile.trust_score}
                  <span style={{fontSize: '0.9rem', color: '#94a3b8'}}>/100</span>
                </div>
              </div>
              {/* Total Alerts */}
              <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px', marginBottom: '8px'}}>
                  <AlertTriangle size={16} /> Tổng Cảnh Báo
                </div>
                <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#ef4444'}}>{profile.total_alerts}</div>
              </div>
              {/* Resolved */}
              <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px', marginBottom: '8px'}}>
                  <TrendingUp size={16} /> Đã Xử Lý
                </div>
                <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#10b981'}}>{profile.resolved_alerts}</div>
              </div>
              {/* Devices */}
              <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px', marginBottom: '8px'}}>
                  <Smartphone size={16} /> Thiết Bị
                </div>
                <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6'}}>{profile.devices.length}</div>
              </div>
            </div>

            {/* Main content: Network Graph + Details */}
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
              {/* Network Graph */}
              <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                <h3 style={{margin: '0 0 12px 0', color: '#fff', fontSize: '14px'}}>
                  <Globe size={16} style={{marginRight: '8px', verticalAlign: 'middle'}} />
                  Mạng lưới chuyển tiền (Bậc 1-2)
                </h3>
                <div style={{height: '280px', overflow: 'hidden'}}>
                  {profile.network_graph.nodes.length > 0 ? (
                    <ForceGraph2D
                      ref={graphRef}
                      width={480}
                      height={280}
                      graphData={profile.network_graph}
                      nodeLabel="name"
                      nodeColor={node => node.group === 1 ? '#3b82f6' : '#f59e0b'}
                      nodeRelSize={8}
                      linkColor={() => '#4b5563'}
                      linkDirectionalArrowLength={3.5}
                      linkDirectionalArrowRelPos={1}
                      backgroundColor="transparent"
                    />
                  ) : (
                    <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#64748b'}}>
                      Không có dữ liệu mạng lưới
                    </div>
                  )}
                </div>
              </div>

              {/* Devices & Recent TX */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                {/* Devices */}
                <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)'}}>
                  <h3 style={{margin: '0 0 12px 0', color: '#fff', fontSize: '14px'}}>
                    <Smartphone size={16} style={{marginRight: '8px', verticalAlign: 'middle'}} />
                    Thiết bị đăng nhập
                  </h3>
                  {profile.devices.map((dev, i) => (
                    <div key={i} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < profile.devices.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'}}>
                      <div>
                        <div style={{color: '#fff', fontSize: '13px', fontWeight: '500'}}>{dev.name}</div>
                        <div style={{color: '#64748b', fontSize: '12px'}}>IP: {dev.ip}</div>
                      </div>
                      <span style={{color: '#94a3b8', fontSize: '12px'}}>{dev.last_seen}</span>
                    </div>
                  ))}
                </div>

                {/* Recent transactions */}
                <div style={{background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)', flex: 1}}>
                  <h3 style={{margin: '0 0 12px 0', color: '#fff', fontSize: '14px'}}>
                    <TrendingUp size={16} style={{marginRight: '8px', verticalAlign: 'middle'}} />
                    Giao dịch gần đây
                  </h3>
                  <div style={{maxHeight: '180px', overflow: 'auto'}}>
                    {profile.recent_transactions.map((tx, i) => (
                      <div key={i} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.03)', fontSize: '13px'}}>
                        <span style={{color: '#94a3b8'}}>{new Date(tx.time).toLocaleTimeString()}</span>
                        <span style={{
                          color: tx.type === 'DEPOSIT' ? '#10b981' : tx.type === 'TRANSFER' ? '#3b82f6' : '#f59e0b',
                          fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                          background: tx.type === 'DEPOSIT' ? 'rgba(16,185,129,0.1)' : tx.type === 'TRANSFER' ? 'rgba(59,130,246,0.1)' : 'rgba(245,158,11,0.1)',
                        }}>
                          {tx.type}
                        </span>
                        <span style={{color: '#fff', fontWeight: '500'}}>${tx.amount.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div style={{textAlign: 'center', padding: '60px', color: '#ef4444'}}>
            Lỗi tải hồ sơ khách hàng
          </div>
        )}
      </div>
    </div>
  );
}
