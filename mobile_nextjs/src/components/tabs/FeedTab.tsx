/* ── Feed Tab – Alert list + Chat panel ─────────────────── */
'use client';

import { createAlertStream, fetchAlerts, fetchChatHistory, fetchStats, sendChatMessage } from '@/lib/api';
import { CATEGORY_ICONS, cn, mapSeverity, SEVERITY_CONFIG, timeAgo } from '@/lib/utils';
import type { Alert, AppSettings, ChatMessage, Severity, Stats } from '@/types';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, ArrowLeft, Bot, ChevronRight, Clock, Loader2, RefreshCw, Search, Send, Sparkles, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

const POLL_INTERVAL = 10000;

function loadSystemPrompt(): string {
    if (typeof window === 'undefined') return '';
    try {
        const raw = localStorage.getItem('ls_settings');
        if (raw) {
            const s: AppSettings = JSON.parse(raw);
            return s.systemPrompt || '';
        }
    } catch { /* */ }
    return '';
}

export function FeedTab() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');
    const [filterSev, setFilterSev] = useState<Severity | 'all'>('all');

    // Chat panel state
    const [chatAlert, setChatAlert] = useState<Alert | null>(null);
    const [chatOpen, setChatOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [chatInput, setChatInput] = useState('');
    const [chatSending, setChatSending] = useState(false);
    const chatScrollRef = useRef<HTMLDivElement>(null);
    const chatInputRef = useRef<HTMLTextAreaElement>(null);

    /* ── Data loading ────────────────────────────────── */
    const loadData = useCallback(async (showLoader = false) => {
        if (showLoader) setLoading(true);
        try {
            const [a, s] = await Promise.all([fetchAlerts(50), fetchStats()]);
            setAlerts(a);
            setStats(s);
            setError('');
        } catch (err: unknown) {
            if (showLoader) setError(err instanceof Error ? err.message : 'Bağlantı hatası');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(true); }, [loadData]);

    useEffect(() => {
        const iv = setInterval(() => loadData(false), POLL_INTERVAL);
        return () => clearInterval(iv);
    }, [loadData]);

    // SSE realtime
    useEffect(() => {
        const es = createAlertStream((alert) => {
            setAlerts((prev) => [alert, ...prev.filter((a) => a.id !== alert.id)]);
        });
        return () => es?.close();
    }, []);

    // Auto scroll chat
    useEffect(() => {
        if (chatScrollRef.current) {
            chatScrollRef.current.scrollTo({ top: chatScrollRef.current.scrollHeight, behavior: 'smooth' });
        }
    }, [messages]);

    /* ── Open chat for an alert ──────────────────────── */
    const openChat = useCallback(async (alert: Alert) => {
        setChatAlert(alert);
        setChatOpen(true);
        setMessages([]);

        // Auto-inject AI analysis as first message
        const report = [
            `🔍 **${alert.title || alert.summary}**`,
            '',
            alert.root_cause ? `**Kök Neden:** ${alert.root_cause}` : '',
            alert.impact ? `**Etki:** ${alert.impact}` : '',
            alert.solution ? `**Çözüm Önerisi:** ${alert.solution}` : '',
            alert.likely_root_cause ? `**Olası Neden:** ${alert.likely_root_cause}` : '',
            (alert.recommended_actions && alert.recommended_actions.length > 0)
                ? `\n**Önerilen Aksiyonlar:**\n${alert.recommended_actions.map((a, i) => `${i + 1}. ${a}`).join('\n')}`
                : '',
            (alert.verification_steps && alert.verification_steps.length > 0)
                ? `\n**Doğrulama Adımları:**\n${alert.verification_steps.map((v, i) => `${i + 1}. ${v}`).join('\n')}`
                : '',
            '',
            'Bu olay hakkında sorularınızı sorabilirsiniz.',
        ].filter(Boolean).join('\n');

        setMessages([{ role: 'assistant', content: report }]);

        // Also load existing chat history
        try {
            const h = await fetchChatHistory(alert.id);
            if (h && h.length > 0) {
                const mappedHistory = h.map((m) => ({
                    role: m.role as 'user' | 'assistant',
                    content: m.content,
                }));
                setMessages((prev) => [...prev, ...mappedHistory]);
            }
        } catch { /* no history yet */ }
    }, []);

    /* ── Send chat message ───────────────────────────── */
    const handleChatSend = useCallback(async (text?: string) => {
        const msg = (text || chatInput).trim();
        if (!msg || chatSending || !chatAlert) return;
        setChatInput('');
        setChatSending(true);
        setMessages((prev) => [...prev, { role: 'user', content: msg }]);

        try {
            const history = messages
                .filter((m) => m.role === 'user' || m.role === 'assistant')
                .slice(-10)
                .map((m) => ({ role: m.role, content: m.content }));
            const systemPrompt = loadSystemPrompt();
            const res = await sendChatMessage(chatAlert.id, msg, history, systemPrompt || undefined);
            setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
        } catch (err: unknown) {
            const errMsg = err instanceof Error ? err.message : 'Yanıt alınamadı';
            setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ Hata: ${errMsg}. Tekrar deneyin.` }]);
        } finally {
            setChatSending(false);
            chatInputRef.current?.focus();
        }
    }, [chatAlert, chatInput, chatSending, messages]);

    /* ── Filtered alerts ─────────────────────────────── */
    const filtered = alerts.filter((a) => {
        const sev = mapSeverity(a.severity);
        if (filterSev !== 'all' && sev !== filterSev) return false;
        if (search) {
            const q = search.toLowerCase();
            return (a.title || a.summary || '').toLowerCase().includes(q)
                || (a.category || '').toLowerCase().includes(q)
                || (a.root_cause || '').toLowerCase().includes(q);
        }
        return true;
    });

    const sevCounts: Record<Severity, number> = { fatal: 0, critical: 0, warn: 0 };
    alerts.forEach((a) => { sevCounts[mapSeverity(a.severity)]++; });

    /* ── Error state ─────────────────────────────────── */
    if (error && alerts.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
                <AlertTriangle className="w-10 h-10 text-red-400/50 mb-3" />
                <p className="text-sm text-white font-semibold mb-1">Bağlantı Hatası</p>
                <p className="text-xs text-surface-600 mb-4">{error}</p>
                <button onClick={() => loadData(true)}
                    className="flex items-center gap-2 text-xs bg-brand-500 text-white px-4 py-2 rounded-lg">
                    <RefreshCw className="w-3.5 h-3.5" /> Tekrar Dene
                </button>
            </div>
        );
    }

    return (
        <div className="relative h-full">
            {/* ── Alert Feed ────────────────────────────── */}
            <div className={cn('transition-all duration-300', chatOpen ? 'opacity-30 pointer-events-none' : '')}>
                {/* Severity pills */}
                <div className="flex gap-2 px-4 pt-3 pb-2">
                    {(['fatal', 'critical', 'warn'] as Severity[]).map((s) => {
                        const cfg = SEVERITY_CONFIG[s];
                        const count = sevCounts[s];
                        const active = filterSev === s;
                        return (
                            <button key={s} onClick={() => setFilterSev(filterSev === s ? 'all' : s)}
                                className={cn(
                                    'flex-1 py-2 rounded-lg text-center transition-all border',
                                    active ? `${cfg.bg} border-current ${cfg.color}` : 'bg-surface-200/50 border-surface-400/50 text-surface-700'
                                )}>
                                <p className={cn('text-lg font-black', active ? cfg.color : 'text-white')}>{count}</p>
                                <p className="text-[9px] font-bold uppercase tracking-wider">{cfg.label}</p>
                            </button>
                        );
                    })}
                </div>

                {/* Search */}
                <div className="px-4 pb-2">
                    <div className="flex items-center gap-2 bg-surface-200/50 rounded-lg px-3 py-2 border border-surface-400/30
                          focus-within:border-brand-500/30 transition-colors">
                        <Search className="w-3.5 h-3.5 text-surface-600 shrink-0" />
                        <input type="text" placeholder="Alert ara..." value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="flex-1 bg-transparent text-xs text-white placeholder:text-surface-600 outline-none" />
                        {search && <button onClick={() => setSearch('')}><X className="w-3 h-3 text-surface-600" /></button>}
                    </div>
                </div>

                {/* Alert list */}
                <div className="px-3 pb-4 space-y-2">
                    {loading ? (
                        [...Array(6)].map((_, i) => (
                            <div key={i} className="skeleton h-16 rounded-lg" />
                        ))
                    ) : filtered.length === 0 ? (
                        <div className="text-center py-16 text-surface-600">
                            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-30" />
                            <p className="text-xs">{search ? 'Sonuç bulunamadı' : 'Henüz alert yok'}</p>
                            {!search && (
                                <button onClick={() => loadData(true)}
                                    className="mt-3 text-[10px] text-brand-400 flex items-center gap-1 mx-auto">
                                    <RefreshCw className="w-3 h-3" /> Yenile
                                </button>
                            )}
                        </div>
                    ) : (
                        filtered.map((alert, i) => {
                            const sev = mapSeverity(alert.severity);
                            const cfg = SEVERITY_CONFIG[sev];
                            return (
                                <motion.button key={alert.id}
                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.03 }}
                                    onClick={() => openChat(alert)}
                                    className={cn(
                                        'w-full text-left bg-surface-200/40 rounded-lg p-3 border-l-[3px] transition-all',
                                        'hover:bg-surface-200/70 active:scale-[0.98]',
                                        sev === 'fatal' && 'border-l-red-500 glow-fatal',
                                        sev === 'critical' && 'border-l-orange-500 glow-critical',
                                        sev === 'warn' && 'border-l-yellow-500',
                                    )}>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={cn('text-[9px] font-black px-1.5 py-0.5 rounded', cfg.bg, cfg.color)}>
                                            {cfg.label}
                                        </span>
                                        <span className="text-[10px] text-surface-600">
                                            {CATEGORY_ICONS[alert.category] || '📋'} {alert.category}
                                        </span>
                                        <span className="ml-auto text-[10px] text-surface-600 flex items-center gap-0.5">
                                            <Clock className="w-2.5 h-2.5" />{timeAgo(alert.created_at || alert.timestamp)}
                                        </span>
                                    </div>
                                    <p className="text-[13px] text-gray-300 font-medium leading-snug line-clamp-2">
                                        {alert.title || alert.summary || 'Analiz bekleniyor...'}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5">
                                        {alert.root_cause && (
                                            <span className="text-[9px] text-surface-600 truncate flex-1">
                                                {alert.root_cause.substring(0, 60)}...
                                            </span>
                                        )}
                                        <ChevronRight className="w-3 h-3 text-surface-600 shrink-0" />
                                    </div>
                                </motion.button>
                            );
                        })
                    )}
                </div>
            </div>

            {/* ── Chat Panel (slide from right) ─────────── */}
            <AnimatePresence>
                {chatOpen && chatAlert && (
                    <motion.div
                        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="absolute inset-0 bg-[var(--theme-bg)] flex flex-col z-20"
                    >
                        {/* Chat header */}
                        <div className="shrink-0 px-3 py-3 border-b border-surface-400/50 flex items-center gap-2">
                            <button onClick={() => setChatOpen(false)}
                                className="p-1.5 rounded-md hover:bg-surface-300 transition-colors">
                                <ArrowLeft className="w-4 h-4" />
                            </button>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                    <Bot className="w-3.5 h-3.5 text-brand-400" />
                                    <span className="text-xs font-bold truncate">AI Asistan</span>
                                </div>
                                <p className="text-[10px] text-surface-600 truncate mt-0.5">
                                    {chatAlert.title || chatAlert.summary}
                                </p>
                            </div>
                            <span className={cn('text-[9px] font-black px-1.5 py-0.5 rounded shrink-0',
                                SEVERITY_CONFIG[mapSeverity(chatAlert.severity)].bg,
                                SEVERITY_CONFIG[mapSeverity(chatAlert.severity)].color)}>
                                {SEVERITY_CONFIG[mapSeverity(chatAlert.severity)].label}
                            </span>
                        </div>

                        {/* Messages */}
                        <div ref={chatScrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
                            {messages.length === 0 && (
                                <div className="text-center py-8">
                                    <Sparkles className="w-8 h-8 text-brand-500/30 mx-auto mb-2" />
                                    <p className="text-xs text-surface-600">AI raporu yükleniyor...</p>
                                </div>
                            )}
                            {messages.map((msg, i) => (
                                <div key={i} className={cn('flex gap-2', msg.role === 'user' ? 'flex-row-reverse' : '')}>
                                    <div className={cn('w-6 h-6 rounded-full flex items-center justify-center shrink-0',
                                        msg.role === 'user' ? 'bg-brand-500/15 text-brand-400' : 'bg-surface-300 text-brand-400')}>
                                        {msg.role === 'user' ? <span className="text-[10px]">👤</span> : <Bot className="w-3 h-3" />}
                                    </div>
                                    <div className={cn('max-w-[85%] rounded-xl px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap',
                                        msg.role === 'user'
                                            ? 'bg-brand-500 text-white rounded-br-sm'
                                            : 'bg-surface-200/60 text-gray-300 rounded-bl-sm border border-surface-400/30')}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {chatSending && (
                                <div className="flex items-center gap-2 px-2">
                                    <div className="flex gap-1">
                                        {[0, 1, 2].map((d) => (
                                            <span key={d} className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce"
                                                style={{ animationDelay: `${d * 150}ms` }} />
                                        ))}
                                    </div>
                                    <span className="text-[10px] text-surface-600">AI düşünüyor...</span>
                                </div>
                            )}
                        </div>

                        {/* Suggested follow-up questions */}
                        {chatAlert.follow_up_questions && chatAlert.follow_up_questions.length > 0 && messages.length <= 2 && (
                            <div className="shrink-0 px-3 pb-2">
                                <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
                                    {chatAlert.follow_up_questions.slice(0, 3).map((q, i) => (
                                        <button key={i} onClick={() => handleChatSend(q)}
                                            className="shrink-0 text-[10px] bg-brand-500/5 text-brand-300 px-2.5 py-1.5 rounded-full
                                               border border-brand-500/10 hover:bg-brand-500/10 transition-colors whitespace-nowrap">
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Input */}
                        <div className="shrink-0 border-t border-surface-400/50 px-3 py-3 safe-bottom">
                            <div className="flex items-end gap-2">
                                <div className="flex-1 bg-surface-200/50 rounded-xl border border-surface-400/30 focus-within:border-brand-500/30">
                                    <textarea ref={chatInputRef} value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChatSend(); } }}
                                        placeholder="Mesajınızı yazın..."
                                        rows={1}
                                        className="w-full bg-transparent text-xs text-white placeholder:text-surface-600 px-3 py-2.5 outline-none resize-none max-h-20" />
                                </div>
                                <button onClick={() => handleChatSend()}
                                    disabled={!chatInput.trim() || chatSending}
                                    className="shrink-0 w-9 h-9 rounded-lg bg-brand-500 text-white flex items-center justify-center
                                       disabled:opacity-30 transition-opacity active:scale-95">
                                    {chatSending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
