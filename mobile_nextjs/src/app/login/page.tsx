/* ── Login Page ─────────────────────────────────────────── */
'use client';

import { useAuth } from '@/lib/auth';
import { motion } from 'framer-motion';
import { Eye, EyeOff, LogIn, Terminal } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function LoginPage() {
    const { login } = useAuth();
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username.trim() || !password.trim()) { setError('Kullanıcı adı ve parola gerekli.'); return; }
        setError(''); setLoading(true);
        try {
            await login(username.trim(), password);
            router.replace('/dashboard');
        } catch (err: any) {
            setError(err.message || 'Geçersiz kullanıcı adı veya parola.');
        } finally { setLoading(false); }
    };

    return (
        <div className="min-h-dvh flex flex-col items-center justify-center px-6 py-10">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-xs">
                {/* Logo */}
                <div className="text-center mb-10">
                    <div className="w-16 h-16 mx-auto mb-3 rounded-2xl bg-primary/10 border border-primary/25
                          flex items-center justify-center">
                        <Terminal className="w-8 h-8 text-primary" />
                    </div>
                    <h1 className="text-xl font-black tracking-tight text-foreground">LogSense AI</h1>
                    <p className="text-xs text-muted-foreground mt-1 font-mono">Infrastructure Monitoring</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="bg-card rounded-lg border border-border flex items-center px-3
                          focus-within:border-primary/40 transition-colors">
                        <span className="text-[13px] text-muted-foreground mr-2 font-mono">$</span>
                        <input type="text" placeholder="username" value={username}
                            onChange={(e) => setUsername(e.target.value)} autoCapitalize="none" autoCorrect="off"
                            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground py-3 outline-none font-mono" />
                    </div>
                    <div className="bg-card rounded-lg border border-border flex items-center px-3
                          focus-within:border-primary/40 transition-colors">
                        <span className="text-[13px] text-muted-foreground mr-2 font-mono">#</span>
                        <input type={showPw ? 'text' : 'password'} placeholder="password" value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground py-3 outline-none font-mono" />
                        <button type="button" onClick={() => setShowPw(!showPw)} className="p-1 text-muted-foreground">
                            {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                    </div>

                    {error && (
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            className="text-red-400 text-xs text-center font-medium">{error}</motion.p>
                    )}

                    <button type="submit" disabled={loading}
                        className="w-full py-3 bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-sm
                       rounded-lg flex items-center justify-center gap-2
                       disabled:opacity-40 active:scale-[0.97] transition-all">
                        {loading
                            ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            : <><LogIn className="w-4 h-4" />Giriş Yap</>}
                    </button>
                </form>

                <p className="text-center text-[10px] text-muted-foreground mt-6 font-mono">
                    demo: admin / logsense123
                </p>
            </motion.div>
        </div>
    );
}
