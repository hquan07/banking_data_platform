import React, { useState, useContext } from 'react';
import { AuthContext } from './AuthContext';
import { ShieldAlert, Lock, User } from 'lucide-react';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useContext(AuthContext);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        
        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const res = await fetch('http://localhost:8000/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData.toString()
            });

            if (!res.ok) {
                throw new Error('Invalid credentials');
            }

            const data = await res.json();
            login(data.access_token, data.role, data.username);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#0b0f19', color: '#fff', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ background: '#141a28', padding: '40px', borderRadius: '12px', width: '100%', maxWidth: '400px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)' }}>
                <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                    <div style={{ display: 'inline-flex', padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '50%', marginBottom: '16px' }}>
                        <ShieldAlert size={32} color="#3b82f6" />
                    </div>
                    <h1 style={{ fontSize: '24px', margin: 0, fontWeight: 600 }}>Banking Platform</h1>
                    <p style={{ color: '#94a3b8', marginTop: '8px', fontSize: '14px' }}>Sign in to continue to the Command Center</p>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {error && (
                        <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '6px', fontSize: '14px', textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                            {error}
                        </div>
                    )}
                    
                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#cbd5e1' }}>Username</label>
                        <div style={{ position: 'relative' }}>
                            <User size={18} style={{ position: 'absolute', left: '12px', top: '10px', color: '#64748b' }} />
                            <input 
                                type="text" 
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                style={{ width: '100%', padding: '10px 10px 10px 40px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', color: '#fff', fontSize: '14px' }}
                                placeholder="Enter username"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#cbd5e1' }}>Password</label>
                        <div style={{ position: 'relative' }}>
                            <Lock size={18} style={{ position: 'absolute', left: '12px', top: '10px', color: '#64748b' }} />
                            <input 
                                type="password" 
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                style={{ width: '100%', padding: '10px 10px 10px 40px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', color: '#fff', fontSize: '14px' }}
                                placeholder="Enter password"
                                required
                            />
                        </div>
                    </div>

                    <button 
                        type="submit" 
                        style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontSize: '15px', fontWeight: 600, cursor: 'pointer', marginTop: '8px', transition: 'background 0.2s' }}
                        onMouseOver={(e) => e.target.style.background = '#2563eb'}
                        onMouseOut={(e) => e.target.style.background = '#3b82f6'}
                    >
                        Sign In
                    </button>
                    
                    <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '13px', color: '#64748b' }}>
                        Default accounts:<br/>
                        admin / admin (ADMIN)<br/>
                        analyst_1 / analyst (ANALYST)
                    </div>
                </form>
            </div>
        </div>
    );
}
