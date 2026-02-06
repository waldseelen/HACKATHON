/* ── LogSense AI – API Service Layer ────────────────────── */

import type { Alert, ChatResponse, HealthResponse, LoginResponse, Stats } from '@/types';

function getApiUrl(): string {
    if (typeof window === 'undefined') {
        const url = process.env.NEXT_PUBLIC_API_URL;
        if (!url) {
            console.warn('[LogSense] NEXT_PUBLIC_API_URL not set, falling back to localhost:8000');
        }
        return url || 'http://localhost:8000';
    }
    if (process.env.NEXT_PUBLIC_API_URL) {
        return process.env.NEXT_PUBLIC_API_URL;
    }
    // In browser, derive from current hostname (works for dev & same-host deploy)
    return `http://${window.location.hostname}:8000`;
}

const API = getApiUrl();

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('ls_token') : null;
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options?.headers as Record<string, string> || {}),
    };

    const res = await fetch(`${API}${path}`, {
        ...options,
        headers,
        signal: options?.signal ?? AbortSignal.timeout(30000),
    });

    if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
            const body = await res.json();
            detail = body.detail || body.message || detail;
        } catch { /* ignore */ }
        throw new Error(detail);
    }
    return res.json();
}

/* ── Auth ───────────────────────────────────────────────── */

export async function login(username: string, password: string): Promise<LoginResponse> {
    return request<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
}

/* ── Alerts ─────────────────────────────────────────────── */

export async function fetchAlerts(limit = 50): Promise<Alert[]> {
    const res = await request<{ data: Alert[]; total: number; has_more: boolean } | Alert[]>(`/alerts?limit=${limit}`);
    // Support both paginated and legacy response formats
    if (Array.isArray(res)) return res;
    return res.data;
}

export async function fetchAlertById(alertId: string): Promise<Alert> {
    return request<Alert>(`/alerts/${alertId}`);
}

export const fetchAlertDetail = fetchAlertById;

/* ── Stats ──────────────────────────────────────────────── */

export async function fetchStats(): Promise<Stats> {
    return request<Stats>('/stats');
}

/* ── Chat ───────────────────────────────────────────────── */

export async function sendChatMessage(
    alertId: string,
    message: string,
    history?: { role: string; content: string }[],
    systemPrompt?: string,
): Promise<ChatResponse> {
    const body: Record<string, unknown> = { alert_id: alertId, message };
    if (history) body.history = history;
    if (systemPrompt) body.system_prompt = systemPrompt;
    return request<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(50000), // Chat AI yanıtı için 50s timeout
    });
}

export async function fetchChatHistory(alertId: string): Promise<{ role: string; content: string; id?: string }[]> {
    try {
        return await request('/chat/' + alertId + '/history');
    } catch {
        return [];
    }
}

/* ── Health ─────────────────────────────────────────────── */

export async function fetchHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
}

/* ── SSE Stream ─────────────────────────────────────────── */

export function createAlertStream(onAlert: (alert: Alert) => void, onError?: (err: Event) => void): EventSource | null {
    if (typeof window === 'undefined') return null;
    try {
        const es = new EventSource(`${API}/alerts/stream`);
        es.onmessage = (event) => {
            try {
                const alert = JSON.parse(event.data) as Alert;
                onAlert(alert);
            } catch { /* ignore parse errors */ }
        };
        if (onError) es.onerror = onError;
        return es;
    } catch {
        return null;
    }
}

export { API as API_URL };

