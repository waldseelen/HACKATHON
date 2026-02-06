import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Notifications from 'expo-notifications';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useRef } from 'react';

import AlertDetailScreen from './src/screens/AlertDetailScreen';
import AlertsScreen from './src/screens/AlertsScreen';
import { registerForPushNotifications } from './src/utils/notifications';

// Handle notifications when app is in foreground
Notifications.setNotificationHandler({
    handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
    }),
});

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

    useEffect(() => {
        // Register for push notifications
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
    }, []);

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
                        options={{ title: '🧠 LogSense AI' }}
                    />
                    <Stack.Screen
                        name="AlertDetail"
                        component={AlertDetailScreen}
                        options={{ title: 'Alert Detail' }}
                    />
                </Stack.Navigator>
            </NavigationContainer>
        </>
    );
}
