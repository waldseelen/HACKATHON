/* ── Settings Tab – System Prompt, Push, Theme ─────────── */
'use client';

import { useAuth } from '@/lib/auth';
import type { AppSettings } from '@/types';
import { motion } from 'framer-motion';
import { Bell, CheckCircle2, Info, Palette, RotateCcw, Terminal } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

const DEFAULT_PROMPT = `Sen bir DevOps ve yazılım güvenliği uzmanısın. Sunucu loglarını analiz edip kısa, net ve uygulanabilir raporlar oluşturuyorsun.
- Sorunun kök nedenini belirle
- Etki alanını ve kapsamını açıkla
- Adım adım çözüm öner
- İlgili servis ve modül isimlerini belirt
- Öncelik sırasına göre aksiyon listesi sun`;

const THEME_OPTIONS: { id: AppSettings['theme']; label: string; icon: string; preview: string }[] = [
    { id: 'dark', label: 'Koyu (Varsayılan)', icon: '🌙', preview: 'bg-[#08090d]' },
    { id: 'midnight', label: 'Midnight Blue', icon: '🌌', preview: 'bg-[#0a0f1a]' },
    { id: 'hacker', label: 'Matrix Green', icon: '💚', preview: 'bg-[#050a05]' },
];

const THEME_VARS: Record<AppSettings['theme'], Record<string, string>> = {
    dark: {
        '--theme-bg': '#08090d',
        '--theme-surface-100': '#0f1015',
        '--theme-surface-200': '#16171e',
        '--theme-brand': '#6C63FF',
        '--theme-watermark': '#6C63FF',
    },
    midnight: {
        '--theme-bg': '#0a0f1a',
        '--theme-surface-100': '#0f1525',
        '--theme-surface-200': '#141c2e',
        '--theme-brand': '#4f8fff',
        '--theme-watermark': '#4f8fff',
    },
    hacker: {
        '--theme-bg': '#050a05',
        '--theme-surface-100': '#0a120a',
        '--theme-surface-200': '#0f180f',
        '--theme-brand': '#00ff41',
        '--theme-watermark': '#00ff41',
    },
};

function loadSettings(): AppSettings {
    if (typeof window === 'undefined') return { systemPrompt: DEFAULT_PROMPT, pushEnabled: true, pushFatalOnly: false, theme: 'dark' };
    try {
        const raw = localStorage.getItem('ls_settings');
        if (raw) return JSON.parse(raw);
    } catch { }
    return { systemPrompt: DEFAULT_PROMPT, pushEnabled: true, pushFatalOnly: false, theme: 'dark' };
}
function saveSettings(s: AppSettings) {
    localStorage.setItem('ls_settings', JSON.stringify(s));
}

export function SettingsTab() {
    const { user, logout } = useAuth();
    const [settings, setSettings] = useState<AppSettings>(loadSettings);
    const [saved, setSaved] = useState(false);

    // Apply theme CSS variables
    useEffect(() => {
        const vars = THEME_VARS[settings.theme] || THEME_VARS.dark;
        const root = document.documentElement;
        Object.entries(vars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        // Apply background color
        document.body.style.backgroundColor = vars['--theme-bg'];
        // Apply brand color
        root.style.setProperty('--color-brand', vars['--theme-brand']);
    }, [settings.theme]);

    const update = useCallback((partial: Partial<AppSettings>) => {
        setSettings((prev) => {
            const next = { ...prev, ...partial };
            saveSettings(next);
            return next;
        });
        flashSaved();
    }, []);

    const flashSaved = () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 1500);
    };

    const resetPrompt = () => {
        update({ systemPrompt: DEFAULT_PROMPT });
    };

    return (
        <div className="p-4 space-y-4 pb-8">
            {/* User card */}
            <div className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-brand-600/30 flex items-center justify-center text-brand-400 font-black text-sm">
                    {user?.username?.charAt(0).toUpperCase() || '?'}
                </div>
                <div className="flex-1">
                    <p className="text-sm font-bold text-white">{user?.username || 'Kullanıcı'}</p>
                    <p className="text-[10px] text-surface-600">{user?.role || 'admin'} • oturum açık</p>
                </div>
                <button onClick={logout} className="text-[10px] text-red-400 font-semibold px-2 py-1 rounded border border-red-400/20 hover:bg-red-400/10 transition">
                    Çıkış
                </button>
            </div>

            {/* System Prompt */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <div className="flex items-center gap-2 mb-3">
                    <Terminal className="w-3.5 h-3.5 text-brand-400" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600">Chatbot System Prompt</h3>
                </div>
                <p className="text-[10px] text-surface-600 mb-2">
                    AI asistanın davranışını ve yanıt stilini bu prompt ile özelleştirebilirsiniz.
                </p>
                <textarea
                    value={settings.systemPrompt}
                    onChange={(e) => update({ systemPrompt: e.target.value })}
                    rows={6}
                    className="w-full bg-surface-100/80 border border-surface-400/30 rounded-lg p-3 text-[11px] font-mono text-white resize-none focus:outline-none focus:border-brand-500/50 placeholder-surface-600 leading-relaxed"
                    placeholder="System prompt girin..."
                />
                <div className="flex items-center gap-2 mt-2">
                    <button onClick={resetPrompt}
                        className="flex items-center gap-1 text-[10px] text-surface-600 hover:text-white transition px-2 py-1 rounded border border-surface-400/20 hover:border-surface-400/40">
                        <RotateCcw className="w-3 h-3" /> Sıfırla
                    </button>
                    <div className="flex-1" />
                    <span className="text-[9px] text-surface-600">{settings.systemPrompt.length} karakter</span>
                </div>
            </motion.div>

            {/* Push Notification Settings */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <div className="flex items-center gap-2 mb-3">
                    <Bell className="w-3.5 h-3.5 text-brand-400" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600">Bildirimler</h3>
                </div>

                <ToggleRow
                    label="Push Bildirimleri"
                    description="Fatal ve Critical hatalar için bildirim al"
                    enabled={settings.pushEnabled}
                    onChange={(v) => update({ pushEnabled: v })}
                />

                <div className="border-t border-surface-400/20 my-2" />

                <ToggleRow
                    label="Yalnızca Fatal"
                    description="Sadece Fatal seviyedeki hatalar için bildirim gönder"
                    enabled={settings.pushFatalOnly}
                    onChange={(v) => update({ pushFatalOnly: v })}
                    disabled={!settings.pushEnabled}
                />
            </motion.div>

            {/* Theme */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <div className="flex items-center gap-2 mb-3">
                    <Palette className="w-3.5 h-3.5 text-brand-400" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600">Tema</h3>
                </div>
                <div className="space-y-2">
                    {THEME_OPTIONS.map((t) => (
                        <button key={t.id}
                            onClick={() => update({ theme: t.id as AppSettings['theme'] })}
                            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-[11px] transition ${settings.theme === t.id
                                ? 'border-brand-500/50 bg-brand-500/10 text-white'
                                : 'border-surface-400/20 text-surface-600 hover:border-surface-400/40 hover:text-white'
                                }`}>
                            <span>{t.icon}</span>
                            <span>{t.label}</span>
                            {settings.theme === t.id && <CheckCircle2 className="w-3 h-3 ml-auto text-brand-400" />}
                        </button>
                    ))}
                </div>
            </motion.div>

            {/* About */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                className="bg-surface-200/40 rounded-lg p-4 border border-surface-400/30">
                <div className="flex items-center gap-2 mb-2">
                    <Info className="w-3.5 h-3.5 text-surface-600" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-surface-600">Hakkında</h3>
                </div>
                <p className="text-[11px] text-surface-600 leading-relaxed">
                    <span className="text-brand-400 font-bold">LogSense</span> — Yapay zeka destekli log analiz platformu.
                    Sunucu hatalarını otomatik kategorize eder, kök neden analizi yapar ve çözüm önerileri sunar.
                </p>
                <p className="text-[9px] text-surface-600 mt-2">v1.0.0 • Hackathon 2025</p>
            </motion.div>

            {/* Save toast */}
            {saved && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                    className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-green-600/90 text-white text-[11px] font-semibold px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-50">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Kaydedildi
                </motion.div>
            )}
        </div>
    );
}

function ToggleRow({ label, description, enabled, onChange, disabled }: {
    label: string; description: string; enabled: boolean;
    onChange: (v: boolean) => void; disabled?: boolean;
}) {
    return (
        <div className={`flex items-center gap-3 py-1 ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="flex-1">
                <p className="text-[11px] text-white font-semibold">{label}</p>
                <p className="text-[9px] text-surface-600">{description}</p>
            </div>
            <button onClick={() => onChange(!enabled)}
                className={`relative w-9 h-5 rounded-full transition-colors ${enabled ? 'bg-brand-500' : 'bg-surface-400/50'}`}>
                <motion.div
                    animate={{ x: enabled ? 16 : 2 }}
                    className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow"
                />
            </button>
        </div>
    );
}
