/* ── LogSense AI – Auth Context ─────────────────────────── */
'use client';

import { login as apiLogin } from '@/lib/api';
import type { User } from '@/types';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const stored = localStorage.getItem('ls_user');
        if (stored) {
            try { setUser(JSON.parse(stored)); } catch { /* */ }
        }
        setLoading(false);
    }, []);

    const login = useCallback(async (username: string, password: string) => {
        const res = await apiLogin(username, password);
        const u: User = { username: res.username, token: res.token };
        setUser(u);
        localStorage.setItem('ls_user', JSON.stringify(u));
        localStorage.setItem('ls_token', res.token);
    }, []);

    const logout = useCallback(() => {
        setUser(null);
        localStorage.removeItem('ls_user');
        localStorage.removeItem('ls_token');
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be inside AuthProvider');
    return ctx;
}
