/* ── Settings Tab – System Prompt, Push, Theme, Code Snippets ── */
'use client';

import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import type { AppSettings } from '@/types';
import { motion } from 'framer-motion';
import { Bell, CheckCircle2, Code2, Github, Info, Moon, Palette, RotateCcw, Sun, Terminal } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

const DEFAULT_PROMPT = `Sen bir DevOps ve yazılım güvenliği uzmanısın. Sunucu loglarını analiz edip kısa, net ve uygulanabilir raporlar oluşturuyorsun.
- Sorunun kök nedenini belirle
- Etki alanını ve kapsamını açıkla
- Adım adım çözüm öner
- İlgili servis ve modül isimlerini belirt
- Öncelik sırasına göre aksiyon listesi sun`;

const DEFAULT_SETTINGS: AppSettings = {
    systemPrompt: DEFAULT_PROMPT,
    pushEnabled: true,
    pushFatalOnly: false,
    theme: 'dark',
    codeSnippetsEnabled: true,
    githubRepoUrl: '',
};

function loadSettings(): AppSettings {
    if (typeof window === 'undefined') return { ...DEFAULT_SETTINGS };
    try {
        const raw = localStorage.getItem('ls_settings');
        if (raw) {
            const parsed = JSON.parse(raw);
            return { ...DEFAULT_SETTINGS, ...parsed };
        }
    } catch { }
    return { ...DEFAULT_SETTINGS };
}
function saveSettings(s: AppSettings) {
    localStorage.setItem('ls_settings', JSON.stringify(s));
}

export function SettingsTab() {
    const { user, logout } = useAuth();
    const { theme, setTheme } = useTheme();
    const [settings, setSettings] = useState<AppSettings>(loadSettings);
    const [saved, setSaved] = useState(false);

    // Sync theme from context
    useEffect(() => {
        if (settings.theme !== theme) {
            setSettings((prev) => ({ ...prev, theme }));
        }
    }, [theme]);

    const update = useCallback((partial: Partial<AppSettings>) => {
        setSettings((prev) => {
            const next = { ...prev, ...partial };
            saveSettings(next);
            // If theme changed, sync to context
            if (partial.theme && partial.theme !== theme) {
                setTheme(partial.theme);
            }
            return next;
        });
        flashSaved();
    }, [theme, setTheme]);

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
            <div className="bg-card/40 rounded-lg p-4 border border-border flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/30 flex items-center justify-center text-primary font-black text-sm">
                    {user?.username?.charAt(0).toUpperCase() || '?'}
                </div>
                <div className="flex-1">
                    <p className="text-sm font-bold text-foreground">{user?.username || 'Kullanıcı'}</p>
                    <p className="text-[10px] text-muted-foreground">{user?.role || 'admin'} • oturum açık</p>
                </div>
                <button onClick={logout} className="text-[10px] text-destructive font-semibold px-2 py-1 rounded border border-destructive/20 hover:bg-destructive/10 transition">
                    Çıkış
                </button>
            </div>

            {/* System Prompt */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-3">
                    <Terminal className="w-3.5 h-3.5 text-primary" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Chatbot System Prompt</h3>
                </div>
                <p className="text-[10px] text-muted-foreground mb-2">
                    AI asistanın davranışını ve yanıt stilini bu prompt ile özelleştirebilirsiniz.
                </p>
                <textarea
                    value={settings.systemPrompt}
                    onChange={(e) => update({ systemPrompt: e.target.value })}
                    rows={6}
                    className="w-full bg-card/80 border border-border rounded-lg p-3 text-[11px] font-mono text-foreground resize-none focus:outline-none focus:border-primary/50 placeholder-muted-foreground leading-relaxed"
                    placeholder="System prompt girin..."
                />
                <div className="flex items-center gap-2 mt-2">
                    <button onClick={resetPrompt}
                        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition px-2 py-1 rounded border border-border/50 hover:border-border">
                        <RotateCcw className="w-3 h-3" /> Sıfırla
                    </button>
                    <div className="flex-1" />
                    <span className="text-[9px] text-muted-foreground">{settings.systemPrompt.length} karakter</span>
                </div>
            </motion.div>

            {/* Push Notification Settings */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-3">
                    <Bell className="w-3.5 h-3.5 text-primary" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Bildirimler</h3>
                </div>

                <ToggleRow
                    label="Push Bildirimleri"
                    description="Fatal ve Critical hatalar için bildirim al"
                    enabled={settings.pushEnabled}
                    onChange={(v) => update({ pushEnabled: v })}
                />

                <div className="border-t border-border/50 my-2" />

                <ToggleRow
                    label="Yalnızca Fatal"
                    description="Sadece Fatal seviyedeki hatalar için bildirim gönder"
                    enabled={settings.pushFatalOnly}
                    onChange={(v) => update({ pushFatalOnly: v })}
                    disabled={!settings.pushEnabled}
                />
            </motion.div>

            {/* Code Snippets Setting */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-3">
                    <Code2 className="w-3.5 h-3.5 text-primary" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Kod Snippet</h3>
                </div>

                <ToggleRow
                    label="Kod Örnekleri Göster"
                    description="AI yanıtlarında kod snippet'larını görüntüle"
                    enabled={settings.codeSnippetsEnabled}
                    onChange={(v) => update({ codeSnippetsEnabled: v })}
                />
            </motion.div>

            {/* GitHub Integration */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-3">
                    <Github className="w-3.5 h-3.5 text-primary" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">GitHub Entegrasyonu</h3>
                </div>
                <p className="text-[10px] text-muted-foreground mb-2">
                    Issue ve PR oluşturmak için GitHub repo URL&apos;nizi girin.
                </p>
                <input
                    type="url"
                    value={settings.githubRepoUrl}
                    onChange={(e) => update({ githubRepoUrl: e.target.value })}
                    placeholder="https://github.com/kullanici/repo"
                    className="w-full bg-card/80 border border-border rounded-lg px-3 py-2.5 text-[11px] font-mono text-foreground focus:outline-none focus:border-primary/50 placeholder-muted-foreground"
                />
                {settings.githubRepoUrl && (
                    <p className="text-[9px] text-green-400 mt-1.5 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Issue ve PR linkleri bu repoya yönlendirilecek
                    </p>
                )}
            </motion.div>

            {/* Theme */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-3">
                    <Palette className="w-3.5 h-3.5 text-primary" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tema</h3>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => update({ theme: 'dark' })}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 rounded-lg border text-[11px] font-semibold transition ${settings.theme === 'dark'
                                ? 'border-primary/50 bg-primary/10 text-foreground'
                                : 'border-border text-muted-foreground hover:border-border hover:text-foreground'
                            }`}>
                        <Moon className="w-4 h-4" />
                        Koyu
                        {settings.theme === 'dark' && <CheckCircle2 className="w-3 h-3 text-primary" />}
                    </button>
                    <button
                        onClick={() => update({ theme: 'light' })}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 rounded-lg border text-[11px] font-semibold transition ${settings.theme === 'light'
                                ? 'border-primary/50 bg-primary/10 text-foreground'
                                : 'border-border text-muted-foreground hover:border-border hover:text-foreground'
                            }`}>
                        <Sun className="w-4 h-4" />
                        Açık
                        {settings.theme === 'light' && <CheckCircle2 className="w-3 h-3 text-primary" />}
                    </button>
                </div>
            </motion.div>

            {/* About */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                className="bg-card/40 rounded-lg p-4 border border-border">
                <div className="flex items-center gap-2 mb-2">
                    <Info className="w-3.5 h-3.5 text-muted-foreground" />
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Hakkında</h3>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                    <span className="text-primary font-bold">LogSense</span> — Yapay zeka destekli log analiz platformu.
                    Sunucu hatalarını otomatik kategorize eder, kök neden analizi yapar ve çözüm önerileri sunar.
                </p>
                <p className="text-[9px] text-muted-foreground mt-2">v1.0.0 • Hackathon 2025</p>
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
                <p className="text-[11px] text-foreground font-semibold">{label}</p>
                <p className="text-[9px] text-muted-foreground">{description}</p>
            </div>
            <button onClick={() => onChange(!enabled)}
                className={`relative w-9 h-5 rounded-full transition-colors ${enabled ? 'bg-primary' : 'bg-muted'}`}>
                <motion.div
                    animate={{ x: enabled ? 16 : 2 }}
                    className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow"
                />
            </button>
        </div>
    );
}
