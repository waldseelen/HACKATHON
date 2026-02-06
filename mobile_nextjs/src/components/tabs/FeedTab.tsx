/* ── Feed Tab – Alert list + Chat panel ─────────────────── */
'use client';

import { createAlertStream, fetchAlerts, fetchChatHistory, fetchStats, sendChatMessage } from '@/lib/api';
import { CATEGORY_ICONS, cn, mapSeverity, SEVERITY_CONFIG, timeAgo } from '@/lib/utils';
import type { Alert, AppSettings, ChatMessage, Severity, Stats } from '@/types';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, ArrowLeft, Bot, ChevronRight, CircleDot, Clock, GitPullRequest, Loader2, RefreshCw, Search, Send, Sparkles, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

const POLL_INTERVAL = 10000;

/** Firestore'dan gelen string veya array alanlarını güvenle array'e çevir */
function ensureArray(val: unknown): string[] {
    if (!val) return [];
    if (Array.isArray(val)) return val.filter(Boolean).map(String);
    if (typeof val === 'string') return val.split(/\n|\s{2,}/).map(s => s.trim()).filter(Boolean);
    return [];
}

function loadSettings(): Partial<AppSettings> {
    if (typeof window === 'undefined') return {};
    try {
        const raw = localStorage.getItem('ls_settings');
        if (raw) return JSON.parse(raw);
    } catch { /* */ }
    return {};
}

function loadSystemPrompt(): string {
    return loadSettings().systemPrompt || '';
}

function loadGithubRepoUrl(): string {
    return loadSettings().githubRepoUrl || '';
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
        const actions = ensureArray(alert.recommended_actions);
        const verSteps = ensureArray(alert.verification_steps);
        const report = [
            `🔍 **${alert.title || alert.summary}**`,
            '',
            alert.root_cause ? `**Kök Neden:** ${alert.root_cause}` : '',
            alert.impact ? `**Etki:** ${alert.impact}` : '',
            alert.solution ? `**Çözüm Önerisi:** ${alert.solution}` : '',
            alert.likely_root_cause ? `**Olası Neden:** ${alert.likely_root_cause}` : '',
            actions.length > 0
                ? `\n**Önerilen Aksiyonlar:**\n${actions.map((a, i) => `${i + 1}. ${a}`).join('\n')}`
                : '',
            verSteps.length > 0
                ? `\n**Doğrulama Adımları:**\n${verSteps.map((v, i) => `${i + 1}. ${v}`).join('\n')}`
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

        // Capture current messages before adding user message
        const currentMessages = [...messages];
        setMessages((prev) => [...prev, { role: 'user', content: msg }]);

        try {
            const history = currentMessages
                .filter((m) => m.role === 'user' || m.role === 'assistant')
                .slice(-10)
                .map((m) => ({ role: m.role, content: m.content }));
            // Add the new user message to history too
            history.push({ role: 'user', content: msg });
            const systemPrompt = loadSystemPrompt();
            const res = await sendChatMessage(chatAlert.id, msg, history, systemPrompt || undefined);
            setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
        } catch (err: unknown) {
            let errMsg = 'Yanıt alınamadı';
            if (err instanceof Error) {
                if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                    errMsg = 'Backend bağlantısı kurulamadı. Sunucunun çalıştığından emin olun.';
                } else if (err.message.includes('timeout') || err.message.includes('504')) {
                    errMsg = 'AI yanıt süresi aşıldı. Model meşgul, lütfen tekrar deneyin.';
                } else if (err.message.includes('503')) {
                    errMsg = 'AI servisi şu anda yoğun. 30 saniye bekleyip tekrar deneyin.';
                } else if (err.message.includes('429')) {
                    errMsg = 'Çok fazla istek. 10 saniye bekleyin.';
                } else {
                    errMsg = err.message;
                }
            }
            setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ **Hata:** ${errMsg}\n\nTekrar göndermek için mesajınızı yazın.` }]);
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
                <AlertTriangle className="w-10 h-10 text-destructive/50 mb-3" />
                <p className="text-sm text-foreground font-semibold mb-1">Bağlantı Hatası</p>
                <p className="text-xs text-muted-foreground mb-4">{error}</p>
                <button onClick={() => loadData(true)}
                    className="flex items-center gap-2 text-xs bg-primary text-primary-foreground px-4 py-2 rounded-lg">
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
                                    active ? `${cfg.bg} ${cfg.border} ${cfg.color}` : 'bg-card/50 border-border text-muted-foreground'
                                )}>
                                <p className={cn('text-lg font-black', active ? cfg.color : 'text-foreground')}>{count}</p>
                                <p className="text-[9px] font-bold uppercase tracking-wider">{cfg.label}</p>
                            </button>
                        );
                    })}
                </div>

                {/* Search */}
                <div className="px-4 pb-2">
                    <div className="flex items-center gap-2 bg-card/50 rounded-lg px-3 py-2 border border-border
                          focus-within:border-primary/30 transition-colors">
                        <Search className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        <input type="text" placeholder="Alert ara..." value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none" />
                        {search && <button onClick={() => setSearch('')}><X className="w-3 h-3 text-muted-foreground" /></button>}
                    </div>
                </div>

                {/* Alert list */}
                <div className="px-3 pb-4 space-y-2">
                    {loading ? (
                        [...Array(6)].map((_, i) => (
                            <div key={i} className="skeleton h-16 rounded-lg" />
                        ))
                    ) : filtered.length === 0 ? (
                        <div className="text-center py-16 text-muted-foreground">
                            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-30" />
                            <p className="text-xs">{search ? 'Sonuç bulunamadı' : 'Henüz alert yok'}</p>
                            {!search && (
                                <button onClick={() => loadData(true)}
                                    className="mt-3 text-[10px] text-primary flex items-center gap-1 mx-auto">
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
                                        'w-full text-left bg-card/40 rounded-lg p-3 border-l-[3px] transition-all',
                                        'hover:bg-card/70 active:scale-[0.98]',
                                        sev === 'fatal' && 'border-l-severity-fatal glow-fatal',
                                        sev === 'critical' && 'border-l-severity-critical glow-critical',
                                        sev === 'warn' && 'border-l-severity-warn',
                                    )}>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={cn('text-[9px] font-black px-1.5 py-0.5 rounded', cfg.bg, cfg.color)}>
                                            {cfg.label}
                                        </span>
                                        <span className="text-[10px] text-muted-foreground">
                                            {CATEGORY_ICONS[alert.category] || '📋'} {alert.category}
                                        </span>
                                        <span className="ml-auto text-[10px] text-muted-foreground flex items-center gap-0.5">
                                            <Clock className="w-2.5 h-2.5" />{timeAgo(alert.created_at || alert.timestamp)}
                                        </span>
                                    </div>
                                    <p className="text-[13px] text-card-foreground font-medium leading-snug line-clamp-2">
                                        {alert.title || alert.summary || 'Analiz bekleniyor...'}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5">
                                        {alert.root_cause && (
                                            <span className="text-[9px] text-muted-foreground truncate flex-1">
                                                {alert.root_cause.substring(0, 60)}...
                                            </span>
                                        )}
                                        <ChevronRight className="w-3 h-3 text-muted-foreground shrink-0" />
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
                        className="chat-panel-overlay bg-background flex flex-col z-50"
                    >
                        {/* Chat header */}
                        <div className="shrink-0 px-3 py-3 border-b border-border flex items-center gap-2">
                            <button onClick={() => setChatOpen(false)}
                                className="p-1.5 rounded-md hover:bg-accent transition-colors">
                                <ArrowLeft className="w-4 h-4" />
                            </button>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                    <Bot className="w-3.5 h-3.5 text-primary" />
                                    <span className="text-xs font-bold truncate text-foreground">AI Asistan</span>
                                </div>
                                <p className="text-[10px] text-muted-foreground truncate mt-0.5">
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
                                    <Sparkles className="w-8 h-8 text-primary/30 mx-auto mb-2" />
                                    <p className="text-xs text-muted-foreground">AI raporu yükleniyor...</p>
                                </div>
                            )}
                            {messages.map((msg, i) => (
                                <div key={i} className={cn('flex gap-2', msg.role === 'user' ? 'flex-row-reverse' : '')}>
                                    <div className={cn('w-6 h-6 rounded-full flex items-center justify-center shrink-0',
                                        msg.role === 'user' ? 'bg-primary/15 text-primary' : 'bg-accent text-primary')}>
                                        {msg.role === 'user' ? <span className="text-[10px]">👤</span> : <Bot className="w-3 h-3" />}
                                    </div>
                                    <div className="max-w-[85%]">
                                        <div className={cn('rounded-xl px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap',
                                            msg.role === 'user'
                                                ? 'bg-primary text-primary-foreground rounded-br-sm'
                                                : 'bg-card/60 text-card-foreground rounded-bl-sm border border-border')}>
                                            {msg.content}
                                        </div>
                                        {/* PR/Issues buttons – only under first AI message */}
                                        {i === 0 && msg.role === 'assistant' && chatAlert && (() => {
                                            const ghUrl = loadGithubRepoUrl();
                                            if (!ghUrl) return null;
                                            const repoBase = ghUrl.replace(/\/$/, '');
                                            return (
                                                <div className="flex gap-2 mt-2">
                                                    <a href={`${repoBase}/issues/new?title=${encodeURIComponent(chatAlert.title || chatAlert.summary || 'Alert')}&body=${encodeURIComponent(`## Alert Detayı\n\n**Severity:** ${chatAlert.severity}\n**Kategori:** ${chatAlert.category}\n**Kök Neden:** ${chatAlert.root_cause || 'Bilinmiyor'}\n\n**Açıklama:**\n${chatAlert.title || chatAlert.summary}\n\n**Çözüm Önerisi:**\n${chatAlert.solution || 'N/A'}`)}`}
                                                        target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1.5 text-[10px] font-semibold px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-accent text-foreground transition-colors">
                                                        <CircleDot className="w-3 h-3 text-severity-warn" />
                                                        Issue Oluştur
                                                    </a>
                                                    <a href={`${repoBase}/compare?expand=1&title=${encodeURIComponent(`fix: ${chatAlert.title || chatAlert.summary || 'Alert fix'}`)}&body=${encodeURIComponent(`## İlgili Alert\n\n**Severity:** ${chatAlert.severity}\n**Kök Neden:** ${chatAlert.root_cause || '-'}\n**Çözüm:** ${chatAlert.solution || '-'}`)}`}
                                                        target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1.5 text-[10px] font-semibold px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/10 hover:bg-primary/20 text-primary transition-colors">
                                                        <GitPullRequest className="w-3 h-3" />
                                                        PR Gönder
                                                    </a>
                                                </div>
                                            );
                                        })()}
                                    </div>
                                </div>
                            ))}
                            {chatSending && (
                                <div className="flex items-center gap-2 px-2">
                                    <div className="flex gap-1">
                                        {[0, 1, 2].map((d) => (
                                            <span key={d} className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
                                                style={{ animationDelay: `${d * 150}ms` }} />
                                        ))}
                                    </div>
                                    <span className="text-[10px] text-muted-foreground">AI düşünüyor...</span>
                                </div>
                            )}
                        </div>

                        {/* Suggested follow-up questions */}
                        {ensureArray(chatAlert.follow_up_questions).length > 0 && messages.length <= 2 && (
                            <div className="shrink-0 px-3 pb-2">
                                <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
                                    {ensureArray(chatAlert.follow_up_questions).slice(0, 3).map((q, i) => (
                                        <button key={i} onClick={() => handleChatSend(q)}
                                            className="shrink-0 text-[10px] bg-primary/5 text-primary px-2.5 py-1.5 rounded-full
                                               border border-primary/10 hover:bg-primary/10 transition-colors whitespace-nowrap">
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Input */}
                        <div className="shrink-0 border-t border-border px-3 py-3 safe-bottom">
                            <div className="flex items-end gap-2">
                                <div className="flex-1 bg-card/50 rounded-xl border border-border focus-within:border-primary/30">
                                    <textarea ref={chatInputRef} value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChatSend(); } }}
                                        placeholder="Mesajınızı yazın..."
                                        rows={1}
                                        className="w-full bg-transparent text-xs text-foreground placeholder:text-muted-foreground px-3 py-2.5 outline-none resize-none max-h-20" />
                                </div>
                                <button onClick={() => handleChatSend()}
                                    disabled={!chatInput.trim() || chatSending}
                                    className="shrink-0 w-9 h-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center
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
