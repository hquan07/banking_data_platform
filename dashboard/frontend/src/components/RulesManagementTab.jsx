import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from './AuthContext';
import { ShieldAlert, ToggleLeft, ToggleRight, Save, RefreshCw } from 'lucide-react';

export default function RulesManagementTab() {
  const { token, user } = useContext(AuthContext);
  const [rules, setRules] = useState([]);
  const [editingRule, setEditingRule] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = () => {
    if (!token) return;
    fetch('http://localhost:8000/api/rules', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setRules(data);
      })
      .catch(console.error);
  };

  const handleEdit = (rule) => {
    setEditingRule(rule.rule_id);
    setEditValues({
      threshold: rule.threshold,
      window_seconds: rule.window_seconds,
      max_count: rule.max_count,
      is_active: rule.is_active,
      description: rule.description || '',
    });
  };

  const handleSave = (ruleId) => {
    setSaving(true);
    setMessage('');
    fetch(`http://localhost:8000/api/rules/${ruleId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(editValues)
    })
      .then(res => res.json())
      .then(data => {
        setMessage(data.message || 'Saved!');
        setEditingRule(null);
        fetchRules();
      })
      .catch(err => setMessage('Error: ' + err.message))
      .finally(() => setSaving(false));
  };

  const handleToggle = (rule) => {
    fetch(`http://localhost:8000/api/rules/${rule.rule_id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ is_active: !rule.is_active })
    })
      .then(() => fetchRules())
      .catch(console.error);
  };

  const isAdmin = user?.role === 'ADMIN';

  return (
    <div className="grid">
      <div className="panel col-span-12">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
          <h2 className="panel-title" style={{margin: 0}}>
            <ShieldAlert size={20} style={{marginRight: '8px', verticalAlign: 'middle'}} />
            Rule Engine Management
          </h2>
          <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
            {message && <span style={{color: '#10b981', fontSize: '13px'}}>{message}</span>}
            <button onClick={fetchRules} style={{background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.3)', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px'}}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {!isAdmin && (
          <div style={{background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', padding: '12px 16px', marginBottom: '1rem', color: '#f59e0b', fontSize: '14px'}}>
            ⚠️ Bạn đang đăng nhập với quyền ANALYST. Chỉ ADMIN mới có thể chỉnh sửa các luật.
          </div>
        )}

        <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
          {rules.map(rule => (
            <div key={rule.rule_id} style={{
              background: rule.is_active ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.01)',
              border: `1px solid ${rule.is_active ? 'rgba(59,130,246,0.2)' : 'rgba(255,255,255,0.05)'}`,
              borderRadius: '12px',
              padding: '1.25rem',
              transition: 'all 0.3s ease',
              opacity: rule.is_active ? 1 : 0.5,
            }}>
              {/* Rule Header */}
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
                  <span style={{
                    fontSize: '1.1rem', fontWeight: 'bold', color: '#fff',
                    display: 'flex', alignItems: 'center', gap: '8px'
                  }}>
                    {rule.name.replace(/_/g, ' ')}
                  </span>
                  <span style={{
                    padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: '600',
                    background: rule.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.15)',
                    color: rule.is_active ? '#10b981' : '#94a3b8',
                  }}>
                    {rule.is_active ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </div>
                {isAdmin && (
                  <div style={{display: 'flex', gap: '8px'}}>
                    <button onClick={() => handleToggle(rule)} style={{
                      background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px',
                      color: rule.is_active ? '#10b981' : '#94a3b8',
                    }}>
                      {rule.is_active ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                    </button>
                    {editingRule !== rule.rule_id ? (
                      <button onClick={() => handleEdit(rule)} style={{
                        background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.3)',
                        padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
                      }}>
                        Edit
                      </button>
                    ) : (
                      <button onClick={() => handleSave(rule.rule_id)} disabled={saving} style={{
                        background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)',
                        padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
                        display: 'flex', alignItems: 'center', gap: '6px',
                      }}>
                        <Save size={14} /> {saving ? 'Saving...' : 'Save'}
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Description */}
              <p style={{color: '#94a3b8', fontSize: '13px', margin: '0 0 1rem 0'}}>{rule.description}</p>

              {/* Parameters */}
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem'}}>
                {/* Threshold */}
                <div style={{background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px 16px'}}>
                  <div style={{color: '#94a3b8', fontSize: '12px', marginBottom: '6px'}}>Ngưỡng giá trị ($)</div>
                  {editingRule === rule.rule_id ? (
                    <input type="number" value={editValues.threshold} onChange={e => setEditValues({...editValues, threshold: parseFloat(e.target.value)})}
                      style={{background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '6px', padding: '8px 12px', color: '#fff', fontSize: '1.1rem', width: '100%', fontWeight: 'bold'}}
                    />
                  ) : (
                    <div style={{color: '#fff', fontSize: '1.25rem', fontWeight: 'bold'}}>${rule.threshold.toLocaleString()}</div>
                  )}
                </div>
                {/* Window */}
                <div style={{background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px 16px'}}>
                  <div style={{color: '#94a3b8', fontSize: '12px', marginBottom: '6px'}}>Cửa sổ thời gian (giây)</div>
                  {editingRule === rule.rule_id ? (
                    <input type="number" value={editValues.window_seconds} onChange={e => setEditValues({...editValues, window_seconds: parseInt(e.target.value)})}
                      style={{background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '6px', padding: '8px 12px', color: '#fff', fontSize: '1.1rem', width: '100%', fontWeight: 'bold'}}
                    />
                  ) : (
                    <div style={{color: '#fff', fontSize: '1.25rem', fontWeight: 'bold'}}>{rule.window_seconds}s</div>
                  )}
                </div>
                {/* Max Count */}
                <div style={{background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px 16px'}}>
                  <div style={{color: '#94a3b8', fontSize: '12px', marginBottom: '6px'}}>Số lần vi phạm tối đa</div>
                  {editingRule === rule.rule_id ? (
                    <input type="number" value={editValues.max_count} onChange={e => setEditValues({...editValues, max_count: parseInt(e.target.value)})}
                      style={{background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '6px', padding: '8px 12px', color: '#fff', fontSize: '1.1rem', width: '100%', fontWeight: 'bold'}}
                    />
                  ) : (
                    <div style={{color: '#fff', fontSize: '1.25rem', fontWeight: 'bold'}}>{rule.max_count}</div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {rules.length === 0 && (
            <div style={{textAlign: 'center', padding: '40px', color: '#64748b'}}>
              Không có dữ liệu Rule. Hệ thống sẽ tự tạo rule mặc định khi khởi động.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
