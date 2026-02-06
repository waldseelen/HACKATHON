/**
 * LogSense AI – Push Notification Setup
 * Registers for Expo push notifications and sends token to backend.
 */

import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { registerPushToken } from '../services/api';

/**
 * Register for push notifications.
 * Gets Expo push token and sends it to the backend.
 */
export async function registerForPushNotifications() {
    // Push notifications only work on physical devices
    if (!Device.isDevice) {
        console.log('Push notifications require a physical device');
        return null;
    }

    try {
        // Check existing permissions
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;

        // Request permissions if not granted
        if (existingStatus !== 'granted') {
            const { status } = await Notifications.requestPermissionsAsync();
            finalStatus = status;
        }

        if (finalStatus !== 'granted') {
            console.log('Push notification permission denied');
            return null;
        }

        // Get Expo push token
        const tokenData = await Notifications.getExpoPushTokenAsync({
            projectId: Constants.expoConfig?.extra?.eas?.projectId,
        });
        const token = tokenData.data;
        console.log('Expo Push Token:', token);

        // Set up Android notification channel
        if (Platform.OS === 'android') {
            await Notifications.setNotificationChannelAsync('alerts', {
                name: 'Alerts',
                importance: Notifications.AndroidImportance.MAX,
                vibrationPattern: [0, 250, 250, 250],
                lightColor: '#FF3B30',
                sound: 'default',
            });
        }

        // Register token with backend
        try {
            const deviceName = `${Device.modelName || 'Unknown'} (${Platform.OS})`;
            await registerPushToken(token, deviceName);
            console.log('Push token registered with backend');
        } catch (err) {
            // Backend might not be running yet — that's OK
            console.log('Could not register token with backend:', err.message);
        }

        return token;
    } catch (error) {
        console.error('Push notification setup error:', error);
        return null;
    }
}
