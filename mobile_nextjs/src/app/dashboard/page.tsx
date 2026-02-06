/* ── Dashboard – 3 Tab Ana Sayfa ────────────────────────── */
'use client';

import { FeedTab } from '@/components/tabs/FeedTab';
import { SettingsTab } from '@/components/tabs/SettingsTab';
import { StatsTab } from '@/components/tabs/StatsTab';
import { useAuth } from '@/lib/auth';
import { BarChart3, LogOut, MessageSquare, Settings, Terminal } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const TABS = [
    { key: 'feed', label: 'Feed', icon: MessageSquare },
    { key: 'stats', label: 'İstatistik', icon: BarChart3 },
    { key: 'settings', label: 'Ayarlar', icon: Settings },
] as const;

type TabKey = typeof TABS[number]['key'];

export default function DashboardPage() {
    const { user, loading, logout } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<TabKey>('feed');

    useEffect(() => {
        if (!loading && !user) router.replace('/login');
    }, [user, loading, router]);

    if (loading || !user) {
        return (
            <div className="min-h-dvh flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-dvh">
            {/* Header */}
            <header className="shrink-0 px-4 py-3 flex items-center justify-between border-b border-surface-400/50">
                <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-brand-500" />
                    <h1 className="text-sm font-black tracking-tight">LogSense</h1>
                    <span className="text-[9px] font-mono text-brand-400 bg-brand-500/10 px-1.5 py-0.5 rounded">AI</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-surface-600 font-mono">{user.username}</span>
                    <button onClick={() => { logout(); router.replace('/login'); }}
                        className="p-1.5 rounded-md hover:bg-surface-300 transition-colors text-surface-600 hover:text-white">
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </header>

            {/* Tab Content */}
            <main className="flex-1 overflow-y-auto overflow-x-hidden">
                {activeTab === 'feed' && <FeedTab />}
                {activeTab === 'stats' && <StatsTab />}
                {activeTab === 'settings' && <SettingsTab />}
            </main>

            {/* Bottom Tab Bar */}
            <nav className="shrink-0 border-t border-surface-400/50 bg-[var(--theme-surface-100)]/95 backdrop-blur-sm safe-bottom">
                <div className="flex">
                    {TABS.map((tab) => {
                        const Icon = tab.icon;
                        const active = activeTab === tab.key;
                        return (
                            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                                className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 transition-colors
                                    ${active ? 'text-brand-500' : 'text-surface-600 hover:text-surface-800'}`}>
                                <Icon className="w-4 h-4" />
                                <span className="text-[10px] font-semibold">{tab.label}</span>
                                {active && <div className="w-4 h-0.5 bg-brand-500 rounded-full mt-0.5" />}
                            </button>
                        );
                    })}
                </div>
            </nav>
        </div>
    );
}
