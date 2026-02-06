import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';

import AlertDetailScreen from './src/screens/AlertDetailScreen';
import AlertsScreen from './src/screens/AlertsScreen';
import ChatScreen from './src/screens/ChatScreen';
import LoginScreen from './src/screens/LoginScreen';

// Notifications only on native (not web)
let Notifications = null;
let registerForPushNotifications = () => { };

if (Platform.OS !== 'web') {
    Notifications = require('expo-notifications');
    registerForPushNotifications = require('./src/utils/notifications').registerForPushNotifications;

    // Handle notifications when app is in foreground
    Notifications.setNotificationHandler({
        handleNotification: async () => ({
            shouldShowAlert: true,
            shouldPlaySound: true,
            shouldSetBadge: true,
        }),
    });
}

const Stack = createNativeStackNavigator();

const THEME = {
    dark: true,
    colors: {
        primary: '#6C63FF',
        background: '#0a0a0a',
        card: '#1a1a1a',
        text: '#ffffff',
        border: '#2a2a2a',
        notification: '#FF3B30',
    },
};

export default function App() {
    const navigationRef = useRef();
    const notificationListener = useRef();
    const responseListener = useRef();
    const [user, setUser] = useState(null);

    useEffect(() => {
        if (!user) return;
        if (Platform.OS === 'web') return; // No push on web

        // Register for push notifications after login
        registerForPushNotifications();

        // Listen for incoming notifications (foreground)
        notificationListener.current =
            Notifications.addNotificationReceivedListener((notification) => {
                console.log('Notification received:', notification.request.content.title);
            });

        // Listen for notification taps
        responseListener.current =
            Notifications.addNotificationResponseReceivedListener((response) => {
                const data = response.notification.request.content.data;
                if (data?.alertId) {
                    navigationRef.current?.navigate('AlertDetail', { alert: data });
                }
            });

        return () => {
            if (notificationListener.current) {
                Notifications.removeNotificationSubscription(notificationListener.current);
            }
            if (responseListener.current) {
                Notifications.removeNotificationSubscription(responseListener.current);
            }
        };
    }, [user]);

    // Login olmamışsa login ekranını göster
    if (!user) {
        return (
            <>
                <StatusBar style="light" />
                <LoginScreen onLogin={(result) => setUser(result)} />
            </>
        );
    }

    return (
        <>
            <StatusBar style="light" />
            <NavigationContainer ref={navigationRef} theme={THEME}>
                <Stack.Navigator
                    screenOptions={{
                        headerStyle: { backgroundColor: '#1a1a1a' },
                        headerTintColor: '#fff',
                        headerTitleStyle: { fontWeight: '700' },
                        contentStyle: { backgroundColor: '#0a0a0a' },
                    }}
                >
                    <Stack.Screen
                        name="Alerts"
                        component={AlertsScreen}
                        options={{
                            title: `🧠 LogSense AI`,
                            headerRight: () => null,
                        }}
                    />
                    <Stack.Screen
                        name="AlertDetail"
                        component={AlertDetailScreen}
                        options={{ title: 'Alert Detayı' }}
                    />
                    <Stack.Screen
                        name="Chat"
                        component={ChatScreen}
                        options={{ title: '💬 AI Sohbet' }}
                    />
                </Stack.Navigator>
            </NavigationContainer>
        </>
    );
}
