import React, { createContext, useEffect, useState } from 'react';

export const AuthContext = createContext();

function isTokenCurrent(token) {
    if (!token) return false;
    try {
        const encoded = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')));
        return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now();
    } catch { return false; }
}

export const AuthProvider = ({ children }) => {
    const storedToken = localStorage.getItem('token');
    const [token, setToken] = useState(isTokenCurrent(storedToken) ? storedToken : null);
    const [user, setUser] = useState(() => {
        if (!isTokenCurrent(storedToken)) { localStorage.removeItem('token'); localStorage.removeItem('user'); return null; }
        const u = localStorage.getItem('user');
        try { return u ? JSON.parse(u) : null; } catch { return null; }
    });

    const login = (access_token, role, username) => {
        setToken(access_token);
        const userData = { role, username };
        setUser(userData);
        localStorage.setItem('token', access_token);
        localStorage.setItem('user', JSON.stringify(userData));
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    };

    useEffect(() => {
        if (!token) return undefined;
        const validate = () => { if (!isTokenCurrent(token)) logout(); };
        const timer = window.setInterval(validate, 30000);
        return () => window.clearInterval(timer);
    }, [token]);

    return (
        <AuthContext.Provider value={{ token, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};
