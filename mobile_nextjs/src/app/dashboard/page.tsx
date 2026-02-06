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
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-dvh overflow-hidden">
            {/* Header */}
            <header className="shrink-0 px-4 py-3 flex items-center justify-between border-b border-border">
                <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-primary" />
                    <h1 className="text-sm font-black tracking-tight text-foreground">LogSense</h1>
                    <span className="text-[9px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">AI</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground font-mono">{user.username}</span>
                    <button onClick={() => { logout(); router.replace('/login'); }}
                        className="p-1.5 rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-foreground">
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </header>

            {/* Tab Content — scrollable within bounds */}
            <main className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
                {activeTab === 'feed' && <FeedTab />}
                {activeTab === 'stats' && <StatsTab />}
                {activeTab === 'settings' && <SettingsTab />}
            </main>

            {/* Bottom Tab Bar — fixed layer at bottom */}
            <nav className="shrink-0 border-t border-border bg-card/95 backdrop-blur-sm safe-bottom z-40">
                <div className="flex">
                    {TABS.map((tab) => {
                        const Icon = tab.icon;
                        const active = activeTab === tab.key;
                        return (
                            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                                className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 transition-colors
                                    ${active ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}>
                                <Icon className="w-4 h-4" />
                                <span className="text-[10px] font-semibold">{tab.label}</span>
                                {active && <div className="w-4 h-0.5 bg-primary rounded-full mt-0.5" />}
                            </button>
                        );
                    })}
                </div>
            </nav>
        </div>
    );
}
