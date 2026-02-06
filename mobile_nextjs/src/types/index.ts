/* ── LogSense AI – Type Definitions ─────────────────────── */

export type Severity = 'fatal' | 'critical' | 'warn';

export type AlertCategory =
    | 'database' | 'network' | 'auth' | 'performance'
    | 'api' | 'infra' | 'build' | 'mobile' | 'security'
    | 'crash' | 'config' | 'unknown';

export interface Alert {
    id: string;
    title: string;
    category: AlertCategory;
    severity: Severity;
    confidence: number;
    dedupe_key: string;
    summary: string;
    one_sentence_summary?: string;
    impact: string;
    root_cause: string;
    likely_root_cause?: string;
    solution: string;
    recommended_actions?: string[];
    action_required: boolean;
    needs_human_review?: boolean;
    verification_steps: string[];
    follow_up_questions: string[];
    context_for_chat: string;
    code_level_hints: string[];
    detected_signals: string[];
    assumptions: string[];
    log_ids: string[];
    raw_log?: string;
    timestamp: string;
    created_at: string;
    notified?: boolean;
    occurrence_count?: number;
}

export interface Stats {
    total_alerts: number;
    severity_counts: Record<string, number>;
    category_counts: Record<string, number>;
    pending_logs: number;
}

export interface ChatMessage {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
}

export interface ChatResponse {
    reply: string;
    alert_id: string;
}

export interface LoginResponse {
    status: string;
    token: string;
    username: string;
    message: string;
}

export interface HealthResponse {
    status: string;
    service: string;
    firebase: boolean;
    ai: boolean;
    pending_logs: number;
    ai_gateway?: {
        provider: string;
        model: string;
        last_call_status: string;
        retry_count_used: number;
        rate_limit_signals: string[];
    };
}

export interface User {
    username: string;
    token: string;
    role?: string;
}

export type FilterState = {
    severity: Severity | 'all';
    category: AlertCategory | 'all';
    search: string;
};

export interface AppSettings {
    systemPrompt: string;
    pushEnabled: boolean;
    pushFatalOnly: boolean;
    theme: 'dark' | 'midnight' | 'hacker';
}
