import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

const SEVERITY_CONFIG = {
    critical: { color: '#FF3B30', icon: 'alert-circle', label: 'CRITICAL' },
    high: { color: '#FF9500', icon: 'warning', label: 'HIGH' },
    medium: { color: '#FFCC00', icon: 'information-circle', label: 'MEDIUM' },
    low: { color: '#34C759', icon: 'checkmark-circle', label: 'LOW' },
};

const CATEGORY_ICONS = {
    database: 'server',
    network: 'wifi',
    auth: 'lock-closed',
    crash: 'skull',
    performance: 'speedometer',
    security: 'shield',
    config: 'settings',
    other: 'code-slash',
};

export default function AlertDetailScreen({ route }) {
    const alert = route.params?.alert || {};
    const severity = alert.severity || 'medium';
    const category = alert.category || 'other';
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
    const categoryIcon = CATEGORY_ICONS[category] || 'code-slash';

    const formatDate = (dateString) => {
        if (!dateString) return 'Unknown';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('tr-TR', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        } catch {
            return dateString;
        }
    };

    return (
        <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
            {/* Severity + Category Header */}
            <View style={[styles.headerBar, { backgroundColor: config.color + '20' }]}>
                <View style={styles.headerRow}>
                    <Ionicons name={config.icon} size={28} color={config.color} />
                    <View style={styles.headerInfo}>
                        <Text style={[styles.severityLabel, { color: config.color }]}>
                            {config.label}
                        </Text>
                        <View style={styles.categoryRow}>
                            <Ionicons name={categoryIcon} size={14} color="#aaa" />
                            <Text style={styles.categoryLabel}>{category}</Text>
                        </View>
                    </View>

                    {/* Confidence */}
                    <View style={styles.confidenceCircle}>
                        <Text style={[styles.confidenceValue, { color: config.color }]}>
                            {Math.round((alert.confidence || 0) * 100)}%
                        </Text>
                        <Text style={styles.confidenceLabel}>confidence</Text>
                    </View>
                </View>
            </View>

            {/* Summary */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Summary</Text>
                <Text style={styles.summaryText}>
                    {alert.summary || 'No summary available'}
                </Text>
            </View>

            {/* Root Cause */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <Ionicons name="search" size={16} color="#FF9500" />
                    <Text style={[styles.sectionTitle, { color: '#FF9500' }]}>
                        Root Cause
                    </Text>
                </View>
                <Text style={styles.bodyText}>
                    {alert.root_cause || 'Analysis not available'}
                </Text>
            </View>

            {/* Solution */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <Ionicons name="build" size={16} color="#34C759" />
                    <Text style={[styles.sectionTitle, { color: '#34C759' }]}>
                        Recommended Solution
                    </Text>
                </View>
                <Text style={styles.bodyText}>
                    {alert.solution || 'No solution available'}
                </Text>
            </View>

            {/* Metadata */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Details</Text>

                <View style={styles.metaRow}>
                    <Text style={styles.metaLabel}>Created</Text>
                    <Text style={styles.metaValue}>{formatDate(alert.created_at)}</Text>
                </View>

                <View style={styles.metaRow}>
                    <Text style={styles.metaLabel}>Action Required</Text>
                    <View style={styles.metaValueRow}>
                        <Ionicons
                            name={alert.action_required ? 'alert-circle' : 'checkmark-circle'}
                            size={16}
                            color={alert.action_required ? '#FF3B30' : '#34C759'}
                        />
                        <Text
                            style={[
                                styles.metaValue,
                                { color: alert.action_required ? '#FF3B30' : '#34C759' },
                            ]}
                        >
                            {alert.action_required ? 'Yes' : 'No'}
                        </Text>
                    </View>
                </View>

                {alert.alertId && (
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Alert ID</Text>
                        <Text style={styles.metaValueMono}>{alert.alertId || alert.id}</Text>
                    </View>
                )}

                {alert.log_ids && alert.log_ids.length > 0 && (
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Related Logs</Text>
                        <Text style={styles.metaValue}>{alert.log_ids.length} log(s)</Text>
                    </View>
                )}
            </View>

            <View style={{ height: 40 }} />
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0a0a0a',
    },
    headerBar: {
        margin: 16,
        borderRadius: 16,
        padding: 20,
    },
    headerRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    headerInfo: {
        marginLeft: 12,
        flex: 1,
    },
    severityLabel: {
        fontSize: 20,
        fontWeight: '900',
        letterSpacing: 1,
    },
    categoryRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 4,
        gap: 4,
    },
    categoryLabel: {
        color: '#aaa',
        fontSize: 13,
        fontWeight: '500',
        textTransform: 'capitalize',
    },
    confidenceCircle: {
        alignItems: 'center',
        backgroundColor: '#0a0a0a80',
        borderRadius: 12,
        paddingHorizontal: 12,
        paddingVertical: 8,
    },
    confidenceValue: {
        fontSize: 20,
        fontWeight: '800',
    },
    confidenceLabel: {
        color: '#666',
        fontSize: 9,
        fontWeight: '600',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    section: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#1a1a1a',
        borderRadius: 12,
        padding: 16,
    },
    sectionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginBottom: 8,
    },
    sectionTitle: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginBottom: 8,
    },
    summaryText: {
        color: '#e0e0e0',
        fontSize: 16,
        lineHeight: 24,
        fontWeight: '500',
    },
    bodyText: {
        color: '#ccc',
        fontSize: 14,
        lineHeight: 22,
    },
    metaRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#2a2a2a',
    },
    metaLabel: {
        color: '#888',
        fontSize: 13,
        fontWeight: '500',
    },
    metaValue: {
        color: '#e0e0e0',
        fontSize: 13,
        fontWeight: '600',
    },
    metaValueRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    metaValueMono: {
        color: '#6C63FF',
        fontSize: 11,
        fontFamily: 'monospace',
    },
});
