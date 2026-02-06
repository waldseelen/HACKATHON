import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    FlatList,
    RefreshControl,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';
import AlertCard from '../components/AlertCard';
import { fetchAlerts, fetchStats } from '../services/api';

const SEVERITY_FILTERS = ['all', 'critical', 'high', 'medium', 'low'];
const AUTO_REFRESH_INTERVAL = 10000; // 10 seconds

export default function AlertsScreen({ navigation }) {
    const [alerts, setAlerts] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');
    const intervalRef = useRef(null);

    const loadData = useCallback(async (showLoader = false) => {
        if (showLoader) setLoading(true);
        setError(null);

        try {
            const [alertsData, statsData] = await Promise.all([
                fetchAlerts(50),
                fetchStats(),
            ]);
            setAlerts(alertsData);
            setStats(statsData);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        loadData(true);
    }, [loadData]);

    // Auto-refresh
    useEffect(() => {
        intervalRef.current = setInterval(() => loadData(false), AUTO_REFRESH_INTERVAL);
        return () => clearInterval(intervalRef.current);
    }, [loadData]);

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        loadData(false);
    }, [loadData]);

    const filteredAlerts =
        filter === 'all'
            ? alerts
            : alerts.filter((a) => a.severity === filter);

    const renderHeader = () => (
        <View style={styles.headerContainer}>
            {/* Stats Cards */}
            {stats && (
                <View style={styles.statsRow}>
                    <StatCard
                        label="Critical"
                        value={stats.severity_counts?.critical || 0}
                        color="#FF3B30"
                    />
                    <StatCard
                        label="High"
                        value={stats.severity_counts?.high || 0}
                        color="#FF9500"
                    />
                    <StatCard
                        label="Medium"
                        value={stats.severity_counts?.medium || 0}
                        color="#FFCC00"
                    />
                    <StatCard
                        label="Low"
                        value={stats.severity_counts?.low || 0}
                        color="#34C759"
                    />
                </View>
            )}

            {/* Filters */}
            <View style={styles.filterRow}>
                {SEVERITY_FILTERS.map((f) => (
                    <TouchableOpacity
                        key={f}
                        style={[
                            styles.filterButton,
                            filter === f && styles.filterButtonActive,
                        ]}
                        onPress={() => setFilter(f)}
                    >
                        <Text
                            style={[
                                styles.filterText,
                                filter === f && styles.filterTextActive,
                            ]}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={styles.sectionTitle}>
                Recent Alerts ({filteredAlerts.length})
            </Text>
        </View>
    );

    if (loading) {
        return (
            <View style={styles.centered}>
                <ActivityIndicator size="large" color="#6C63FF" />
                <Text style={styles.loadingText}>Loading alerts...</Text>
            </View>
        );
    }

    if (error) {
        return (
            <View style={styles.centered}>
                <Ionicons name="cloud-offline" size={48} color="#FF3B30" />
                <Text style={styles.errorTitle}>Connection Error</Text>
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity
                    style={styles.retryButton}
                    onPress={() => loadData(true)}
                >
                    <Text style={styles.retryText}>Retry</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <FlatList
            data={filteredAlerts}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
                <AlertCard
                    alert={item}
                    onPress={() => navigation.navigate('AlertDetail', { alert: item })}
                />
            )}
            ListHeaderComponent={renderHeader}
            ListEmptyComponent={
                <View style={styles.centered}>
                    <Ionicons name="checkmark-circle" size={48} color="#34C759" />
                    <Text style={styles.emptyTitle}>All Clear!</Text>
                    <Text style={styles.emptyText}>No alerts to show</Text>
                </View>
            }
            refreshControl={
                <RefreshControl
                    refreshing={refreshing}
                    onRefresh={onRefresh}
                    tintColor="#6C63FF"
                    colors={['#6C63FF']}
                />
            }
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
        />
    );
}

function StatCard({ label, value, color }) {
    return (
        <View style={[styles.statCard, { borderTopColor: color }]}>
            <Text style={[styles.statValue, { color }]}>{value}</Text>
            <Text style={styles.statLabel}>{label}</Text>
        </View>
    );
}

const styles = StyleSheet.create({
    listContent: {
        paddingBottom: 20,
    },
    headerContainer: {
        paddingTop: 8,
        paddingBottom: 4,
    },
    statsRow: {
        flexDirection: 'row',
        paddingHorizontal: 16,
        gap: 8,
        marginBottom: 12,
    },
    statCard: {
        flex: 1,
        backgroundColor: '#1a1a1a',
        borderRadius: 10,
        padding: 12,
        alignItems: 'center',
        borderTopWidth: 3,
    },
    statValue: {
        fontSize: 22,
        fontWeight: '800',
    },
    statLabel: {
        color: '#888',
        fontSize: 10,
        fontWeight: '600',
        marginTop: 2,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    filterRow: {
        flexDirection: 'row',
        paddingHorizontal: 16,
        gap: 6,
        marginBottom: 16,
    },
    filterButton: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
        backgroundColor: '#1a1a1a',
    },
    filterButtonActive: {
        backgroundColor: '#6C63FF',
    },
    filterText: {
        color: '#888',
        fontSize: 12,
        fontWeight: '600',
    },
    filterTextActive: {
        color: '#fff',
    },
    sectionTitle: {
        color: '#888',
        fontSize: 12,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 1,
        paddingHorizontal: 20,
        marginBottom: 8,
    },
    centered: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 40,
    },
    loadingText: {
        color: '#888',
        marginTop: 12,
        fontSize: 14,
    },
    errorTitle: {
        color: '#FF3B30',
        fontSize: 18,
        fontWeight: '700',
        marginTop: 12,
    },
    errorText: {
        color: '#888',
        fontSize: 13,
        marginTop: 6,
        textAlign: 'center',
    },
    retryButton: {
        marginTop: 16,
        backgroundColor: '#6C63FF',
        paddingHorizontal: 24,
        paddingVertical: 10,
        borderRadius: 8,
    },
    retryText: {
        color: '#fff',
        fontWeight: '700',
        fontSize: 14,
    },
    emptyTitle: {
        color: '#34C759',
        fontSize: 18,
        fontWeight: '700',
        marginTop: 12,
    },
    emptyText: {
        color: '#888',
        fontSize: 13,
        marginTop: 4,
    },
});
