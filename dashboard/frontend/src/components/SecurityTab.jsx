import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from './AuthContext';
import { ChevronDown, ChevronUp, Upload, MessageSquare, UserCheck } from 'lucide-react';
import KYCProfile from './KYCProfile';

export default function SecurityTab() {
  const { token } = useContext(AuthContext);
  const [pgAlerts, setPgAlerts] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedAlert, setExpandedAlert] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [selectedAssignee, setSelectedAssignee] = useState('');
  const [users, setUsers] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [kycAccountId, setKycAccountId] = useState(null);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [selectedAlerts, setSelectedAlerts] = useState([]);
  const [caseError, setCaseError] = useState('');
  const [loadingCases, setLoadingCases] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const itemsPerPage = 7;

  useEffect(() => {
    const timeout = setTimeout(() => { setCurrentPage(1); setDebouncedSearch(searchText.trim()); }, 350);
    return () => clearTimeout(timeout);
  }, [searchText]);

  useEffect(() => {
    fetchAlerts();
    fetchUsers();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, [currentPage, debouncedSearch, token]);

  const fetchAlerts = () => {
    if (!token) return;
    setLoadingCases(true);
    const params = new URLSearchParams({ page: currentPage, limit: itemsPerPage });
    if (debouncedSearch) params.set('search', debouncedSearch);
    fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(async res => { if (!res.ok) throw new Error((await res.json()).detail || 'Cannot load cases'); return res.json(); })
      .then(data => {
        if (data.data) {
          setPgAlerts(data.data);
          setTotalAlerts(data.total);
        } else if (Array.isArray(data)) {
          setPgAlerts(data);
          setTotalAlerts(data.length);
        }
        setCaseError('');
      })
      .catch(err => setCaseError(err.message))
      .finally(() => setLoadingCases(false));
  };

  const fetchUsers = () => {
    if (!token) return;
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/users', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setUsers(data);
      })
      .catch(console.error);
  };

  const handleUpdateStatus = (id, status, notes = null, assigneeId = null) => {
    const current = pgAlerts.find(item => item.alert_id === id);
    if (!current) return;
    const body = { status, version: current.version };
    if (notes) body.notes = notes;
    if (assigneeId) body.assignee_id = parseInt(assigneeId);

    fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts/${id}/status`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    }).then(async res => {
      if (!res.ok) throw new Error((await res.json()).detail || 'Case update failed');
      fetchAlerts();
      setExpandedAlert(null);
      setNoteText('');
      setSelectedAssignee('');
      setCaseError('');
    }).catch(err => { setCaseError(err.message); fetchAlerts(); });
  };

  const handleBulkResolve = () => {
    if (selectedAlerts.length === 0) return;
    if (!window.confirm(`Xác nhận RESOLVED ${selectedAlerts.length} cảnh báo?`)) return;
    
    Promise.all(
      selectedAlerts.map(id => {
        const current = pgAlerts.find(item => item.alert_id === id);
        if (!current || current.status !== 'INVESTIGATING') return Promise.resolve();
        return (
        fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts/${id}/status`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ status: 'RESOLVED', version: current.version })
        })
        .then(async res => { if (!res.ok) throw new Error((await res.json()).detail || 'Bulk update failed'); })
        );
      })
    ).then(() => {
      fetchAlerts();
      setSelectedAlerts([]);
    }).catch(err => { setCaseError(err.message); fetchAlerts(); });
  };

  const handleUploadEvidence = async (alertId) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.png,.jpg,.jpeg,.doc,.docx';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      setUploading(true);
      try {
        // Step 1: Get presigned URL from backend
        const res = await fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/evidence/presigned-url?filename=${encodeURIComponent(file.name)}&alert_id=${alertId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Could not prepare evidence upload');
        const { upload_url, object_key } = await res.json();

        // Step 2: Upload directly to MinIO via presigned URL
        const uploadRes = await fetch(upload_url, {
          method: 'PUT',
          body: file,
          headers: { 'Content-Type': 'application/octet-stream' }
        });
        if (!uploadRes.ok) throw new Error('Evidence upload failed');

        const completeRes = await fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/alerts/${alertId}/evidence/complete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ object_key })
        });
        if (!completeRes.ok) throw new Error((await completeRes.json()).detail || 'Evidence confirmation failed');

        alert(`✅ File "${file.name}" đã được upload thành công!`);
        fetchAlerts();
      } catch (err) {
        alert('❌ Lỗi upload: ' + err.message);
      } finally {
        setUploading(false);
      }
    };
    input.click();
  };

  const handleExportCSV = () => {
    fetch((window._env_?.API_URL || 'http://localhost:8000') + '/api/alerts/export', {
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

  const parseXAI = (xaiStr) => {
    if (!xaiStr) return null;
    try {
      return JSON.parse(xaiStr);
    } catch {
      return [xaiStr];
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalAlerts / itemsPerPage));
  const currentAlerts = pgAlerts;

  return (
    <div className="grid">
      {/* KYC Modal */}
      {kycAccountId && (
        <KYCProfile accountId={kycAccountId} onClose={() => setKycAccountId(null)} />
      )}

      {/* Alert Feed (Case Management) */}
      <div className="panel col-span-12">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <h2 className="panel-title" style={{margin: 0}}>Case Management (Postgres)</h2>
          <button onClick={handleExportCSV} style={{background: '#10b981', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold'}}>
            Export CSV
          </button>
        </div>
        
        {selectedAlerts.length > 0 && (
          <div style={{marginTop: '12px', padding: '12px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <span style={{color: '#10b981', fontWeight: 'bold'}}>{selectedAlerts.length} alerts selected</span>
            <button onClick={handleBulkResolve} style={{background: '#10b981', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold'}}>
              Resolve Selected
            </button>
          </div>
        )}
        <label style={{display: 'block', marginTop: 12, color: '#cbd5e1'}}>
          Tìm theo account, payment hoặc rule
          <input
            type="search"
            value={searchText}
            onChange={event => setSearchText(event.target.value)}
            maxLength={100}
            style={{display: 'block', width: '100%', maxWidth: 360, marginTop: 6, padding: 8, borderRadius: 6}}
          />
        </label>
        {caseError && <p role="alert" style={{color: '#ef4444'}}>{caseError}</p>}
        {loadingCases && <p role="status" style={{color: '#94a3b8'}}>Đang tải cases...</p>}

        <div style={{overflowX: 'visible'}}>
          <table style={{width: '100%', textAlign: 'left', borderCollapse: 'collapse', marginTop: '1rem'}}>
            <thead>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8'}}>
                <th style={{padding: '8px', width: '40px'}}>
                  <input 
                    type="checkbox" 
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedAlerts(currentAlerts.filter(a => a.status === 'INVESTIGATING').map(a => a.alert_id));
                      } else {
                        setSelectedAlerts([]);
                      }
                    }}
                    checked={currentAlerts.filter(a => a.status === 'INVESTIGATING').length > 0 && selectedAlerts.length === currentAlerts.filter(a => a.status === 'INVESTIGATING').length}
                  />
                </th>
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
                <React.Fragment key={alert.alert_id}>
                  <tr style={{borderBottom: '1px solid rgba(255,255,255,0.05)'}}>
                    <td style={{padding: '12px 8px'}}>
                      {alert.status === 'INVESTIGATING' && (
                        <input 
                          type="checkbox" 
                          checked={selectedAlerts.includes(alert.alert_id)}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedAlerts(prev => [...prev, alert.alert_id]);
                            else setSelectedAlerts(prev => prev.filter(id => id !== alert.alert_id));
                          }}
                        />
                      )}
                    </td>
                    <td style={{padding: '12px 8px'}}>#{alert.alert_id}</td>
                    <td style={{padding: '12px 8px'}}>{new Date(alert.created_at).toLocaleTimeString()}</td>
                    <td style={{padding: '12px 8px'}}>
                      <button onClick={() => setKycAccountId(alert.account_id)} style={{
                        background: 'transparent', border: 'none', color: '#3b82f6',
                        fontWeight: 'bold', cursor: 'pointer', textDecoration: 'underline',
                        fontSize: '14px', padding: 0,
                      }}>
                        {alert.account_id}
                      </button>
                    </td>
                    <td style={{padding: '12px 8px', color: '#f59e0b'}}>{alert.rule_name}</td>
                    <td style={{padding: '12px 8px', position: 'relative'}}>
                      <span className="risk-badge-wrapper" style={{position: 'relative', cursor: 'help'}}>
                        <span style={{padding: '2px 8px', borderRadius: '12px', background: alert.risk_score > 90 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)', color: alert.risk_score > 90 ? '#ef4444' : '#f59e0b'}}>
                          {alert.risk_score}
                        </span>
                        {/* XAI Tooltip */}
                        {alert.xai_explanation && (
                          <div className="xai-tooltip">
                            <div style={{fontWeight: 'bold', marginBottom: '6px', color: '#f59e0b', fontSize: '12px'}}>🧠 Giải thích AI (XAI)</div>
                            {parseXAI(alert.xai_explanation)?.map((reason, i) => (
                              <div key={i} style={{color: '#e2e8f0', fontSize: '12px', marginBottom: '4px', paddingLeft: '8px', borderLeft: '2px solid rgba(245,158,11,0.3)'}}>
                                {reason}
                              </div>
                            ))}
                          </div>
                        )}
                      </span>
                    </td>
                    <td style={{padding: '12px 8px'}}>
                      <span style={{color: alert.status === 'RESOLVED' ? '#10b981' : alert.status === 'IGNORED' ? '#94a3b8' : '#3b82f6'}}>
                        {alert.status}
                      </span>
                    </td>
                    <td style={{padding: '12px 8px'}}>
                      {alert.status === 'PENDING' ? (
                        <div style={{display: 'flex', gap: '8px'}}>
                          <button onClick={() => handleUpdateStatus(alert.alert_id, 'INVESTIGATING')} style={{background: '#3b82f6', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px'}}>Start Investigation</button>
                          <button onClick={() => handleUpdateStatus(alert.alert_id, 'IGNORED')} style={{background: '#64748b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px'}}>Ignore</button>
                        </div>
                      ) : alert.status === 'INVESTIGATING' ? (
                        <div style={{display: 'flex', gap: '8px'}}>
                          <button 
                            onClick={() => setExpandedAlert(expandedAlert === alert.alert_id ? null : alert.alert_id)}
                            style={{background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.3)', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px'}}
                          >
                            Investigate {expandedAlert === alert.alert_id ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                          </button>
                          <button 
                            onClick={() => handleUpdateStatus(alert.alert_id, 'IGNORED')}
                            style={{background: '#64748b', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px'}}
                          >
                            Ignore
                          </button>
                        </div>
                      ) : (
                        alert.notes && <span style={{color: '#94a3b8', fontSize: '12px'}}>📝 Has notes</span>
                      )}
                    </td>
                  </tr>

                  {/* Expandable Investigation Panel */}
                  {expandedAlert === alert.alert_id && alert.status === 'INVESTIGATING' && (
                    <tr>
                      <td colSpan="7" style={{padding: '0 8px 12px 8px'}}>
                        <div style={{
                          background: 'rgba(59,130,246,0.03)', border: '1px solid rgba(59,130,246,0.15)',
                          borderRadius: '8px', padding: '16px', marginTop: '4px',
                        }}>
                          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem'}}>
                            {/* Notes */}
                            <div>
                              <label style={{color: '#94a3b8', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px'}}>
                                <MessageSquare size={14} /> Ghi chú điều tra
                              </label>
                              <textarea
                                value={noteText}
                                onChange={(e) => setNoteText(e.target.value)}
                                placeholder="Nhập ghi chú điều tra..."
                                style={{
                                  width: '100%', height: '80px', background: 'rgba(0,0,0,0.3)',
                                  border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px',
                                  color: '#fff', padding: '8px', fontSize: '13px', resize: 'none',
                                }}
                              />
                            </div>
                            {/* Assign */}
                            <div>
                              <label style={{color: '#94a3b8', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px'}}>
                                <UserCheck size={14} /> Giao việc cho
                              </label>
                              <select
                                value={selectedAssignee}
                                onChange={(e) => setSelectedAssignee(e.target.value)}
                                style={{
                                  width: '100%', background: 'rgba(0,0,0,0.3)',
                                  border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px',
                                  color: '#fff', padding: '10px', fontSize: '13px',
                                }}
                              >
                                <option value="">-- Chọn nhân viên --</option>
                                {users.map(u => (
                                  <option key={u.id} value={u.id}>{u.username} ({u.role})</option>
                                ))}
                              </select>

                              <button
                                onClick={() => handleUploadEvidence(alert.alert_id)}
                                disabled={uploading}
                                style={{
                                  marginTop: '8px', width: '100%',
                                  background: 'rgba(139,92,246,0.1)', color: '#8b5cf6',
                                  border: '1px solid rgba(139,92,246,0.3)', padding: '8px',
                                  borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                }}
                              >
                                <Upload size={14} /> {uploading ? 'Đang upload...' : 'Upload Chứng cứ (PDF/Ảnh)'}
                              </button>
                              {alert.evidence_file_url && (
                                <div style={{marginTop: '6px', fontSize: '12px', color: '#10b981'}}>
                                  📎 Đã có file đính kèm
                                </div>
                              )}
                            </div>
                            {/* Action buttons */}
                            <div style={{display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: '8px'}}>
                              <button
                                onClick={() => handleUpdateStatus(alert.alert_id, 'RESOLVED', noteText, selectedAssignee)}
                                style={{
                                  background: 'rgba(16,185,129,0.15)', color: '#10b981',
                                  border: '1px solid rgba(16,185,129,0.3)', padding: '10px',
                                  borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 'bold',
                                }}
                              >
                                ✅ Resolve (Xác nhận vi phạm)
                              </button>
                              <button
                                onClick={() => handleUpdateStatus(alert.alert_id, 'IGNORED', noteText, selectedAssignee)}
                                style={{
                                  background: 'rgba(100,116,139,0.15)', color: '#94a3b8',
                                  border: '1px solid rgba(100,116,139,0.3)', padding: '10px',
                                  borderRadius: '6px', cursor: 'pointer', fontSize: '14px',
                                }}
                              >
                                ❌ Ignore (Báo động giả)
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {!loadingCases && !caseError && pgAlerts.length === 0 && (
                <tr><td colSpan="8" style={{textAlign: 'center', padding: '20px', color: '#64748b'}}>Không có case phù hợp.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination Controls */}
        {totalAlerts > 0 && (
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)'}}>
            <span style={{color: '#94a3b8', fontSize: '0.875rem'}}>
              Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, totalAlerts)} of {totalAlerts} entries
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

    </div>
  );
}
