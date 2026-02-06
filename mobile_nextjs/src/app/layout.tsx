/* ── Root Layout ────────────────────────────────────────── */
import { CodeWatermark } from '@/components/CodeWatermark';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AuthProvider } from '@/lib/auth';
import { ThemeProvider } from '@/lib/theme';
import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'LogSense AI',
    description: 'AI-Powered Infrastructure Monitoring',
    manifest: '/manifest.json',
    icons: {
        icon: '/favicon.svg',
        apple: '/icon-192.svg',
    },
};

export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    themeColor: '#08090d',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="tr" className="dark" suppressHydrationWarning>
            <body className="min-h-dvh">
                <ErrorBoundary>
                    <ThemeProvider>
                        <CodeWatermark />
                        <AuthProvider>
                            <div className="app-shell relative z-10">
                                {children}
                            </div>
                        </AuthProvider>
                    </ThemeProvider>
                </ErrorBoundary>
            </body>
        </html>
    );
}
