/* ── Theme Provider – shadcn-style dark/light toggle ──── */
'use client';

import type { AppSettings } from '@/types';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextValue {
    theme: Theme;
    setTheme: (t: Theme) => void;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getStoredTheme(): Theme {
    if (typeof window === 'undefined') return 'dark';
    try {
        const raw = localStorage.getItem('ls_settings');
        if (raw) {
            const s: AppSettings = JSON.parse(raw);
            if (s.theme === 'light' || s.theme === 'dark') return s.theme;
        }
    } catch { /* */ }
    return 'dark';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState<Theme>('dark');

    useEffect(() => {
        const stored = getStoredTheme();
        setThemeState(stored);
        applyTheme(stored);
    }, []);

    const setTheme = useCallback((t: Theme) => {
        setThemeState(t);
        applyTheme(t);
        // Persist
        try {
            const raw = localStorage.getItem('ls_settings');
            const s = raw ? JSON.parse(raw) : {};
            s.theme = t;
            localStorage.setItem('ls_settings', JSON.stringify(s));
        } catch { /* */ }
    }, []);

    const toggleTheme = useCallback(() => {
        setTheme(theme === 'dark' ? 'light' : 'dark');
    }, [theme, setTheme]);

    return (
        <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

function applyTheme(t: Theme) {
    const root = document.documentElement;
    if (t === 'dark') {
        root.classList.add('dark');
        root.classList.remove('light');
    } else {
        root.classList.remove('dark');
        root.classList.add('light');
    }
}

export function useTheme() {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be inside ThemeProvider');
    return ctx;
}
