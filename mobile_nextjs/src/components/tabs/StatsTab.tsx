/* ── Stats Tab – Charts & Metrics ───────────────────────── */
'use client';

import { fetchAlerts, fetchStats } from '@/lib/api';
import { CATEGORY_ICONS, formatDate, mapSeverity, SEVERITY_CONFIG } from '@/lib/utils';
import type { Alert, Severity, Stats } from '@/types';
import { motion } from 'framer-motion';
import { Activity, AlertTriangle, Clock } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

const SEV_COLORS: Record<Severity, string> = {
    fatal: '#FF3B30',
    critical: '#FF9500',
    warn: '#FFCC00',
};

export function StatsTab() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [s, a] = await Promise.all([fetchStats(), fetchAlerts(100)]);
            setStats(s);
            setAlerts(a);
        } catch { } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    if (loading) return (
        <div className="p-4 space-y-3">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-lg" />)}
        </div>
    );

    if (!stats) return (
        <div className="p-8 text-center text-surface-600 text-xs">
            <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-30" />
            İstatistik yüklenemedi
            <button onClick={load} className="block mx-auto mt-2 text-brand-400 text-xs">Tekrar Dene</button>
        </div>
    );

    // Compute 3-tier severity counts
    const sevCounts: Record<Severity, number> = { fatal: 0, critical: 0, warn: 0 };
    Object.entries(stats.severity_counts).forEach(([k, v]) => {
        sevCounts[mapSeverity(k)] += v;
    });
    const total = Object.values(sevCounts).reduce((a, b) => a + b, 0);

    // Category counts
    const catEntries = Object.entries(stats.category_counts).sort((a, b) => b[1] - a[1]);

    // Timeline: count alerts per hour (last 24h)
    const now = Date.now();
    const hourBuckets = new Array(24).fill(0);
    alerts.forEach((a) => {
        try {
            const h = Math.floor((now - new Date(a.created_at || a.timestamp).getTime()) / 3600000);
            if (h >= 0 && h < 24) hourBuckets[23 - h]++;
        } catch { }
    });
    const maxBucket = Math.max(...hourBuckets, 1);

    return (
        <div className="p-4 space-y-4 pb-8">
            {/* Overview cards */}
            <div className="grid grid-cols-3 gap-2">
                <StatCard icon={<AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
                    label="Toplam" value={String(total)} />
                <StatCard icon={<Clock className="w-3.5 h-3.5 text-orange-400" />}
                    label="Bekleyen" value={String(stats.pending_logs)} />
                <StatCard icon={<Activity className="w-3.5 h-3.5 text-brand-400" />}
                    label="Kategori" value={String(catEntries.length)} />
            </div>

            {/* Donut chart */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600 mb-3">Severity Dağılımı</h3>
                <div className="flex items-center gap-4">
                    {/* SVG Donut */}
                    <div className="w-24 h-24 shrink-0">
                        <DonutChart data={sevCounts} colors={SEV_COLORS} total={total} />
                    </div>
                    {/* Legend */}
                    <div className="space-y-2 flex-1">
                        {(['fatal', 'critical', 'warn'] as Severity[]).map((s) => {
                            const pct = total > 0 ? Math.round((sevCounts[s] / total) * 100) : 0;
                            return (
                                <div key={s} className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SEV_COLORS[s] }} />
                                    <span className="text-[11px] text-surface-800 flex-1">{SEVERITY_CONFIG[s].label}</span>
                                    <span className="text-[11px] font-bold text-white">{sevCounts[s]}</span>
                                    <span className="text-[10px] text-surface-600 w-8 text-right">{pct}%</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </motion.div>

            {/* Category breakdown */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600 mb-3">Kategori Dağılımı</h3>
                <div className="space-y-2">
                    {catEntries.map(([cat, count]) => {
                        const pct = total > 0 ? (count / total) * 100 : 0;
                        return (
                            <div key={cat}>
                                <div className="flex items-center justify-between mb-0.5">
                                    <span className="text-[11px] text-surface-800">
                                        {CATEGORY_ICONS[cat] || '📋'} {cat}
                                    </span>
                                    <span className="text-[11px] font-bold text-white">{count}</span>
                                </div>
                                <div className="h-1 bg-surface-400/30 rounded-full overflow-hidden">
                                    <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                                        transition={{ duration: 0.6, delay: 0.2 }}
                                        className="h-full bg-brand-500 rounded-full" />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </motion.div>

            {/* Timeline (last 24h) */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600 mb-3">Son 24 Saat</h3>
                <div className="flex items-end gap-[2px] h-16">
                    {hourBuckets.map((count, i) => (
                        <motion.div key={i}
                            initial={{ height: 0 }} animate={{ height: `${(count / maxBucket) * 100}%` }}
                            transition={{ duration: 0.4, delay: i * 0.02 }}
                            className="flex-1 bg-brand-500/60 rounded-t-sm min-h-[2px] hover:bg-brand-500 transition-colors" />
                    ))}
                </div>
                <div className="flex justify-between mt-1">
                    <span className="text-[8px] text-surface-600">24s önce</span>
                    <span className="text-[8px] text-surface-600">şimdi</span>
                </div>
            </motion.div>

            {/* Recent fatal/critical list */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600 mb-3">Son Fatal & Critical</h3>
                <div className="space-y-2">
                    {alerts
                        .filter((a) => { const s = mapSeverity(a.severity); return s === 'fatal' || s === 'critical'; })
                        .slice(0, 5)
                        .map((a) => {
                            const sev = mapSeverity(a.severity);
                            return (
                                <div key={a.id} className="flex items-center gap-2 text-[11px]">
                                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: SEV_COLORS[sev] }} />
                                    <span className="flex-1 truncate text-surface-800">{a.title || a.summary}</span>
                                    <span className="text-surface-600 shrink-0">{formatDate(a.created_at || a.timestamp)}</span>
                                </div>
                            );
                        })}
                    {alerts.filter((a) => { const s = mapSeverity(a.severity); return s === 'fatal' || s === 'critical'; }).length === 0 && (
                        <p className="text-[11px] text-surface-600 text-center py-2">Henüz yok</p>
                    )}
                </div>
            </motion.div>
        </div>
    );
}

/* ── Helper components ─────────────────────────────────── */

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
    return (
        <div className="bg-surface-200/40 rounded-lg p-3 border border-surface-400/30 text-center">
            <div className="flex justify-center mb-1">{icon}</div>
            <p className="text-base font-black">{value}</p>
            <p className="text-[9px] text-surface-600 uppercase tracking-wide font-semibold">{label}</p>
        </div>
    );
}

function DonutChart({ data, colors, total }: { data: Record<Severity, number>; colors: Record<Severity, string>; total: number }) {
    const radius = 36;
    const stroke = 8;
    const circumference = 2 * Math.PI * radius;
    let offset = 0;

    const segments = (['fatal', 'critical', 'warn'] as Severity[]).filter((s) => data[s] > 0);

    return (
        <svg viewBox="0 0 96 96" className="w-full h-full -rotate-90">
            {/* Background ring */}
            <circle cx="48" cy="48" r={radius} fill="none" stroke="#1a1a1a" strokeWidth={stroke} />
            {/* Data segments */}
            {segments.map((s) => {
                const pct = total > 0 ? data[s] / total : 0;
                const dashArray = `${circumference * pct} ${circumference * (1 - pct)}`;
                const dashOffset = -offset * circumference;
                const el = (
                    <circle key={s} cx="48" cy="48" r={radius} fill="none"
                        stroke={colors[s]} strokeWidth={stroke} strokeLinecap="round"
                        strokeDasharray={dashArray} strokeDashoffset={dashOffset} />
                );
                offset += pct;
                return el;
            })}
            {/* Center text */}
            <text x="48" y="48" textAnchor="middle" dominantBaseline="central"
                className="fill-white font-black text-lg rotate-90 origin-center" fontSize="18">
                {total}
            </text>
        </svg>
    );
}
