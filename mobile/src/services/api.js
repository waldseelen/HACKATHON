/**
 * LogSense AI – API Service (v2)
 * Handles all communication with the backend.
 * Includes: alerts, stats, push tokens, chat, login
 */

import { Platform } from 'react-native';

// Auto-detect backend URL in development
const getApiUrl = () => {
    if (__DEV__) {
        try {
            const Constants = require('expo-constants').default;
            const debuggerHost = Constants.expoConfig?.hostUri?.split(':')[0];
            if (debuggerHost) {
                return `http://${debuggerHost}:8000`;
            }
        } catch {
            // Web or Constants unavailable
        }
        // Web dev: same host, different port
        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            const host = window.location.hostname;
            return `http://${host}:8000`;
        }
    }
    return 'http://10.200.124.242:8000';
};

const API_URL = getApiUrl();

// ── Auth ─────────────────────────────────────────────────

/**
 * Login with username/password.
 */
export async function login(username, password) {
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('login error:', error);
        throw error;
    }
}

// ── Alerts ───────────────────────────────────────────────

/**
 * Fetch recent alerts from the backend.
 */
export async function fetchAlerts(limit = 50) {
    try {
        const response = await fetch(`${API_URL}/alerts?limit=${limit}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('fetchAlerts error:', error);
        throw error;
    }
}

/**
 * Fetch a single alert by ID.
 */
export async function fetchAlertById(alertId) {
    try {
        const response = await fetch(`${API_URL}/alerts/${alertId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('fetchAlertById error:', error);
        throw error;
    }
}

/**
 * Fetch dashboard stats.
 */
export async function fetchStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('fetchStats error:', error);
        throw error;
    }
}

// ── Push Tokens ──────────────────────────────────────────

/**
 * Register Expo push token with the backend.
 */
export async function registerPushToken(token, deviceName = 'unknown') {
    try {
        const response = await fetch(`${API_URL}/register-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token,
                device_name: deviceName,
                platform: 'expo',
            }),
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('registerPushToken error:', error);
        throw error;
    }
}

// ── Chat ─────────────────────────────────────────────────

/**
 * Send a chat message about an alert. Returns AI reply.
 */
export async function sendChatMessage(alertId, message, history = null) {
    try {
        const body = { alert_id: alertId, message };
        if (history) body.history = history;

        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('sendChatMessage error:', error);
        throw error;
    }
}

/**
 * Fetch chat history for an alert.
 */
export async function fetchChatHistory(alertId) {
    try {
        const response = await fetch(`${API_URL}/chat/${alertId}/history`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('fetchChatHistory error:', error);
        throw error;
    }
}

// ── Logs ─────────────────────────────────────────────────

/**
 * Fetch recent logs.
 */
export async function fetchRecentLogs(limit = 20) {
    try {
        const response = await fetch(`${API_URL}/logs/recent?limit=${limit}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('fetchRecentLogs error:', error);
        throw error;
    }
}

export { API_URL };

