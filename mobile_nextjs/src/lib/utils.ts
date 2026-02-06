/* ── LogSense AI – Utility helpers ──────────────────────── */

import type { Severity } from '@/types';
import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
    return clsx(inputs);
}

/* ── Severity helpers ──────────────────────────────────── */

export const SEVERITY_CONFIG: Record<Severity, { color: string; bg: string; label: string; dot: string; ring: string; border: string }> = {
    fatal: { color: 'text-severity-fatal', bg: 'bg-severity-fatal/10', label: 'FATAL', dot: 'bg-severity-fatal', ring: 'ring-severity-fatal/30', border: 'border-severity-fatal' },
    critical: { color: 'text-severity-critical', bg: 'bg-severity-critical/10', label: 'CRITICAL', dot: 'bg-severity-critical', ring: 'ring-severity-critical/30', border: 'border-severity-critical' },
    warn: { color: 'text-severity-warn', bg: 'bg-severity-warn/10', label: 'WARN', dot: 'bg-severity-warn', ring: 'ring-severity-warn/30', border: 'border-severity-warn' },
};

/** Map backend severity values to our 3-tier system */
export function mapSeverity(raw: string): Severity {
    const s = (raw || '').toLowerCase();
    if (s === 'fatal' || s === 'error') return 'fatal';
    if (s === 'critical' || s === 'high') return 'critical';
    return 'warn'; // medium, low, info, etc.
}

/** Whether this severity warrants push notification */
export function shouldPush(sev: Severity): boolean {
    return sev === 'fatal' || sev === 'critical';
}

export const CATEGORY_ICONS: Record<string, string> = {
    database: '🗄️', network: '🌐', auth: '🔒', performance: '⚡',
    api: '☁️', infra: '🖥️', build: '🔧', mobile: '📱', unknown: '❓',
    crash: '💀', security: '🛡️', config: '⚙️', other: '📋',
};

/* ── Time helpers ──────────────────────────────────────── */

export function timeAgo(dateString: string): string {
    if (!dateString) return '';
    try {
        const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
        return `${Math.floor(seconds / 86400)}d`;
    } catch { return ''; }
}

export function formatDate(dateString: string): string {
    if (!dateString) return 'Bilinmiyor';
    try {
        return new Date(dateString).toLocaleString('tr-TR', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
        });
    } catch { return dateString; }
}

/* ── Code watermark lines ──────────────────────────────── */
export const WATERMARK_LINES = [
    'try { await db.connect(); }',
    'if (err.code === "ECONNRESET")',
    'logger.fatal("OOM killed")',
    'catch (TimeoutException e)',
    'SELECT * FROM health_check',
    'panic: runtime error',
    'SIGKILL received PID=1',
    'nginx: [error] upstream',
    'kubectl rollout restart',
    'gc overhead limit exceeded',
    'Connection refused :5432',
    'SSL handshake failed',
    'Too many open files',
    'disk usage 97% /dev/sda1',
    'OOMKilled container_id=',
    'HTTP 503 Service Unavailable',
    'redis.exceptions.ConnectionError',
    'kafka.errors.NoBrokersAvailable',
    'max_connections reached',
    'certificate has expired',
];
