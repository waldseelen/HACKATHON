/**
 * LogSense AI – API Service
 * Handles all communication with the backend.
 */

import Constants from 'expo-constants';

// Auto-detect backend URL in development
const getApiUrl = () => {
    if (__DEV__) {
        // Expo Go: use the dev server host IP
        const debuggerHost = Constants.expoConfig?.hostUri?.split(':')[0];
        if (debuggerHost) {
            return `http://${debuggerHost}:8000`;
        }
    }
    // Fallback / production - use your machine's local IP
    // Get QR code with: curl http://localhost:8000/qr -o qr.png
    return 'http://10.200.124.242:8000';
};

const API_URL = getApiUrl();

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

