import React, { useState, useContext, useEffect } from 'react';
import { AuthContext } from './AuthContext';
import { ShieldAlert, Lock, User, Activity, Database, Zap, AlertTriangle } from 'lucide-react';

// --- Inline CSS for Animations ---
const styles = `
  @keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  @keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
    100% { transform: translateY(0px); }
  }

  @keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
    70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
    100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
    20%, 40%, 60%, 80% { transform: translateX(5px); }
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .login-container {
    display: flex;
    height: 100vh;
    width: 100vw;
    background: #0b0f19;
    color: #fff;
    overflow: hidden;
  }

  .left-panel {
    flex: 1.2;
    background: linear-gradient(-45deg, #0f172a, #1e1b4b, #0f172a);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 10%;
    position: relative;
  }

  .particles {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
      radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 20%),
      radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08) 0%, transparent 20%);
    pointer-events: none;
  }

  .right-panel {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0b0f19;
    position: relative;
  }

  .glass-card {
    background: rgba(20, 26, 40, 0.6);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 48px;
    width: 100%;
    max-width: 440px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    position: relative;
    z-index: 10;
  }

  .glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  }

  .input-group {
    position: relative;
    margin-bottom: 24px;
  }

  .input-field {
    width: 100%;
    padding: 14px 14px 14px 44px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    color: #fff;
    font-size: 15px;
    transition: all 0.3s ease;
  }

  .input-field:focus {
    outline: none;
    border-color: #3b82f6;
    background: rgba(15, 23, 42, 0.9);
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
  }

  .input-icon {
    position: absolute;
    left: 14px;
    top: 14px;
    color: #64748b;
    transition: color 0.3s ease;
  }

  .input-field:focus + .input-icon {
    color: #3b82f6;
  }

  .submit-btn {
    width: 100%;
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    color: #fff;
    border: none;
    padding: 14px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
  }

  .submit-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px -10px rgba(99, 102, 241, 0.6);
  }

  .submit-btn:active {
    transform: translateY(0);
  }

  .submit-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }

  .feature-item {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    animation: float 6s ease-in-out infinite;
  }
  .feature-item:nth-child(2) { animation-delay: -2s; }
  .feature-item:nth-child(3) { animation-delay: -4s; }

  .feature-icon-wrapper {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
  }

  @media (max-width: 900px) {
    .left-panel { display: none; }
    .right-panel { flex: 1; padding: 24px; }
  }
`;

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [shake, setShake] = useState(false);
    
    const { login } = useContext(AuthContext);

    // Inject CSS
    useEffect(() => {
        const styleSheet = document.createElement("style");
        styleSheet.innerText = styles;
        document.head.appendChild(styleSheet);
        return () => styleSheet.remove();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        
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
                throw new Error('Incorrect username or password');
            }

            const data = await res.json();
            login(data.access_token, data.role, data.username);
        } catch (err) {
            setError(err.message);
            setShake(true);
            setTimeout(() => setShake(false), 500); // Remove shake class after animation
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-container">
            {/* LEFT PANEL: Branding & Features */}
            <div className="left-panel">
                <div className="particles"></div>
                
                <div style={{ position: 'relative', zIndex: 2 }}>
                    <div style={{ 
                        display: 'inline-flex', padding: '16px', 
                        background: 'linear-gradient(135deg, rgba(59,130,246,0.2) 0%, rgba(99,102,241,0.2) 100%)', 
                        borderRadius: '20px', marginBottom: '32px',
                        border: '1px solid rgba(255,255,255,0.1)',
                        animation: 'pulseGlow 3s infinite'
                    }}>
                        <ShieldAlert size={40} color="#60a5fa" />
                    </div>
                    
                    <h1 style={{ fontSize: '48px', fontWeight: 800, margin: '0 0 16px 0', lineHeight: 1.1, letterSpacing: '-1px' }}>
                        Banking Data<br/>
                        <span style={{ color: '#60a5fa' }}>Command Center</span>
                    </h1>
                    <p style={{ fontSize: '18px', color: '#94a3b8', maxWidth: '400px', marginBottom: '64px', lineHeight: 1.6 }}>
                        Advanced fraud detection, real-time analytics, and KYC monitoring in a single unified platform.
                    </p>

                    <div>
                        <div className="feature-item">
                            <div className="feature-icon-wrapper">
                                <Activity size={24} color="#60a5fa" />
                            </div>
                            <div>
                                <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 600 }}>Real-time Monitoring</h3>
                                <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>Process over 10k+ TPS instantly</p>
                            </div>
                        </div>
                        
                        <div className="feature-item">
                            <div className="feature-icon-wrapper">
                                <Zap size={24} color="#a78bfa" />
                            </div>
                            <div>
                                <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 600 }}>AI-Powered Detection</h3>
                                <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>XAI-explained fraud alerts</p>
                            </div>
                        </div>

                        <div className="feature-item">
                            <div className="feature-icon-wrapper">
                                <Database size={24} color="#34d399" />
                            </div>
                            <div>
                                <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 600 }}>Multi-DB Analytics</h3>
                                <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>Postgres, Neo4j & ClickHouse</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT PANEL: Login Form */}
            <div className="right-panel">
                {/* Decorative background blur blobs */}
                <div style={{ position: 'absolute', top: '20%', right: '20%', width: '300px', height: '300px', background: 'rgba(59, 130, 246, 0.15)', filter: 'blur(100px)', borderRadius: '50%' }}></div>
                <div style={{ position: 'absolute', bottom: '20%', left: '20%', width: '300px', height: '300px', background: 'rgba(139, 92, 246, 0.15)', filter: 'blur(100px)', borderRadius: '50%' }}></div>

                <div className="glass-card" style={{ animation: shake ? 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both' : 'none' }}>
                    <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                        <h2 style={{ fontSize: '28px', fontWeight: 700, margin: '0 0 8px 0' }}>Welcome back</h2>
                        <p style={{ color: '#94a3b8', margin: 0, fontSize: '15px' }}>Please enter your details to sign in</p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        {error && (
                            <div style={{ 
                                padding: '14px', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', 
                                borderRadius: '12px', fontSize: '14px', marginBottom: '24px', 
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                display: 'flex', alignItems: 'center', gap: '8px'
                            }}>
                                <AlertTriangle size={18} />
                                {error}
                            </div>
                        )}
                        
                        <div className="input-group">
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#cbd5e1', fontWeight: 500 }}>Username</label>
                            <input 
                                type="text" 
                                className="input-field"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter username"
                                required
                            />
                            <User className="input-icon" size={18} />
                        </div>

                        <div className="input-group">
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#cbd5e1', fontWeight: 500 }}>Password</label>
                            <input 
                                type="password" 
                                className="input-field"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />
                            <Lock className="input-icon" size={18} />
                        </div>

                        <button 
                            type="submit" 
                            className="submit-btn"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <svg style={{ animation: 'spin 1s linear infinite', width: '20px', height: '20px' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeOpacity="0.25"></circle>
                                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Signing in...
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
