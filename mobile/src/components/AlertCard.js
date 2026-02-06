import { Ionicons } from '@expo/vector-icons';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

const SEVERITY_CONFIG = {
    critical: { color: '#FF3B30', icon: 'alert-circle', bg: '#FF3B3020' },
    high: { color: '#FF9500', icon: 'warning', bg: '#FF950020' },
    medium: { color: '#FFCC00', icon: 'information-circle', bg: '#FFCC0020' },
    low: { color: '#34C759', icon: 'checkmark-circle', bg: '#34C75920' },
};

const CATEGORY_ICONS = {
    database: 'server',
    network: 'wifi',
    auth: 'lock-closed',
    performance: 'speedometer',
    api: 'cloud',
    infra: 'hardware-chip',
    build: 'construct',
    mobile: 'phone-portrait',
    unknown: 'code-slash',
    crash: 'skull',
    security: 'shield',
    config: 'settings',
    other: 'code-slash',
};

function timeAgo(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    } catch {
        return '';
    }
}

export default function AlertCard({ alert, onPress }) {
    const severity = alert.severity || 'medium';
    const category = alert.category || 'other';
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
    const categoryIcon = CATEGORY_ICONS[category] || 'code-slash';

    return (
        <TouchableOpacity
            style={[styles.card, { borderLeftColor: config.color }]}
            onPress={onPress}
            activeOpacity={0.7}
        >
            <View style={styles.header}>
                <View style={[styles.severityBadge, { backgroundColor: config.bg }]}>
                    <Ionicons name={config.icon} size={14} color={config.color} />
                    <Text style={[styles.severityText, { color: config.color }]}>
                        {severity.toUpperCase()}
                    </Text>
                </View>

                <View style={styles.categoryBadge}>
                    <Ionicons name={categoryIcon} size={12} color="#aaa" />
                    <Text style={styles.categoryText}>{category}</Text>
                </View>

                <Text style={styles.time}>{timeAgo(alert.created_at)}</Text>
            </View>

            <Text style={styles.summary} numberOfLines={2}>
                {alert.title || alert.summary || 'Özet yok'}
            </Text>

            <View style={styles.footer}>
                <View style={styles.confidenceBar}>
                    <View
                        style={[
                            styles.confidenceFill,
                            {
                                width: `${(alert.confidence || 0) * 100}%`,
                                backgroundColor: config.color,
                            },
                        ]}
                    />
                </View>
                <Text style={styles.confidenceText}>
                    {Math.round((alert.confidence || 0) * 100)}%
                </Text>

                {alert.action_required && (
                    <View style={styles.actionBadge}>
                        <Text style={styles.actionText}>ACTION</Text>
                    </View>
                )}
            </View>
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    card: {
        backgroundColor: '#1a1a1a',
        borderRadius: 12,
        padding: 16,
        marginHorizontal: 16,
        marginVertical: 6,
        borderLeftWidth: 4,
        elevation: 4,
        ...Platform.select({
            web: {
                boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.3)',
            },
            default: {
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 2 },
                shadowOpacity: 0.3,
                shadowRadius: 4,
            },
        }),
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 10,
    },
    severityBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 6,
        gap: 4,
    },
    severityText: {
        fontSize: 11,
        fontWeight: '800',
        letterSpacing: 0.5,
    },
    categoryBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        marginLeft: 8,
        gap: 4,
    },
    categoryText: {
        color: '#aaa',
        fontSize: 12,
        fontWeight: '500',
    },
    time: {
        color: '#666',
        fontSize: 11,
        marginLeft: 'auto',
    },
    summary: {
        color: '#e0e0e0',
        fontSize: 14,
        lineHeight: 20,
        marginBottom: 10,
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    confidenceBar: {
        flex: 1,
        height: 4,
        backgroundColor: '#333',
        borderRadius: 2,
        overflow: 'hidden',
    },
    confidenceFill: {
        height: '100%',
        borderRadius: 2,
    },
    confidenceText: {
        color: '#888',
        fontSize: 11,
        fontWeight: '600',
        width: 32,
        textAlign: 'right',
    },
    actionBadge: {
        backgroundColor: '#FF3B3030',
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 4,
    },
    actionText: {
        color: '#FF3B30',
        fontSize: 9,
        fontWeight: '800',
        letterSpacing: 0.5,
    },
});
