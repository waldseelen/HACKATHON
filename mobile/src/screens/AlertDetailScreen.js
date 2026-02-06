import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

const SEVERITY_CONFIG = {
    critical: { color: '#FF3B30', icon: 'alert-circle', label: 'P0 CRITICAL' },
    high: { color: '#FF9500', icon: 'warning', label: 'P1 HIGH' },
    medium: { color: '#FFCC00', icon: 'information-circle', label: 'P2 MEDIUM' },
    low: { color: '#34C759', icon: 'checkmark-circle', label: 'P3 LOW' },
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
    // v1 uyumlu
    crash: 'skull',
    security: 'shield',
    config: 'settings',
    other: 'code-slash',
};

export default function AlertDetailScreen({ route, navigation }) {
    const alert = route.params?.alert || {};
    const severity = alert.severity || 'medium';
    const category = alert.category || 'unknown';
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
    const categoryIcon = CATEGORY_ICONS[category] || 'code-slash';

    const formatDate = (dateString) => {
        if (!dateString) return 'Bilinmiyor';
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

    // İlgili alanları çıkar
    const actions = alert.solution
        ? alert.solution.split('\n').filter(Boolean)
        : alert.recommended_actions || [];
    const verificationSteps = alert.verification_steps || [];
    const followUpQuestions = alert.follow_up_questions || [];
    const impact = alert.impact || '';
    const title = alert.title || alert.summary || 'Alert Detayı';
    const dedupeKey = alert.dedupe_key || '';
    const detectedSignals = alert.detected_signals || [];
    const assumptions = alert.assumptions || [];
    const codeHints = alert.code_level_hints || [];

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

                    <View style={styles.confidenceCircle}>
                        <Text style={[styles.confidenceValue, { color: config.color }]}>
                            {Math.round((alert.confidence || 0) * 100)}%
                        </Text>
                        <Text style={styles.confidenceLabel}>güven</Text>
                    </View>
                </View>

                {/* Title */}
                {title && (
                    <Text style={styles.titleText} numberOfLines={2}>
                        {title}
                    </Text>
                )}
            </View>

            {/* Özet */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Özet</Text>
                <Text style={styles.summaryText}>
                    {alert.summary || 'Özet yok'}
                </Text>
            </View>

            {/* Etki */}
            {impact ? (
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Ionicons name="flash" size={16} color="#FF3B30" />
                        <Text style={[styles.sectionTitle, { color: '#FF3B30' }]}>Etki</Text>
                    </View>
                    <Text style={styles.bodyText}>{impact}</Text>
                </View>
            ) : null}

            {/* Kök Neden */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <Ionicons name="search" size={16} color="#FF9500" />
                    <Text style={[styles.sectionTitle, { color: '#FF9500' }]}>Kök Neden</Text>
                </View>
                <Text style={styles.bodyText}>
                    {alert.root_cause || 'Analiz mevcut değil'}
                </Text>
            </View>

            {/* Önerilen Aksiyonlar */}
            {actions.length > 0 && (
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Ionicons name="build" size={16} color="#34C759" />
                        <Text style={[styles.sectionTitle, { color: '#34C759' }]}>
                            Önerilen Aksiyonlar
                        </Text>
                    </View>
                    {actions.map((action, i) => (
                        <View key={i} style={styles.listItem}>
                            <Text style={styles.listBullet}>{i + 1}.</Text>
                            <Text style={styles.listText}>{action}</Text>
                        </View>
                    ))}
                </View>
            )}

            {/* Doğrulama Adımları */}
            {verificationSteps.length > 0 && (
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Ionicons name="checkmark-done" size={16} color="#6C63FF" />
                        <Text style={[styles.sectionTitle, { color: '#6C63FF' }]}>
                            Doğrulama Adımları
                        </Text>
                    </View>
                    {verificationSteps.map((step, i) => (
                        <View key={i} style={styles.listItem}>
                            <Ionicons name="checkbox-outline" size={14} color="#6C63FF" />
                            <Text style={styles.listText}>{step}</Text>
                        </View>
                    ))}
                </View>
            )}

            {/* Kod İpuçları */}
            {codeHints.length > 0 && (
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Ionicons name="code-slash" size={16} color="#00BCD4" />
                        <Text style={[styles.sectionTitle, { color: '#00BCD4' }]}>
                            Kod İpuçları
                        </Text>
                    </View>
                    {codeHints.map((hint, i) => (
                        <View key={i} style={styles.codeHint}>
                            <Text style={styles.codeHintText}>{hint}</Text>
                        </View>
                    ))}
                </View>
            )}

            {/* Tespit Edilen Sinyaller */}
            {detectedSignals.length > 0 && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Sinyaller</Text>
                    <View style={styles.tagsRow}>
                        {detectedSignals.map((signal, i) => (
                            <View key={i} style={styles.tag}>
                                <Text style={styles.tagText}>{signal}</Text>
                            </View>
                        ))}
                    </View>
                </View>
            )}

            {/* Varsayımlar */}
            {assumptions.length > 0 && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Varsayımlar</Text>
                    {assumptions.map((a, i) => (
                        <Text key={i} style={styles.assumptionText}>• {a}</Text>
                    ))}
                </View>
            )}

            {/* Metadata */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Detaylar</Text>

                <View style={styles.metaRow}>
                    <Text style={styles.metaLabel}>Oluşturulma</Text>
                    <Text style={styles.metaValue}>{formatDate(alert.created_at)}</Text>
                </View>

                <View style={styles.metaRow}>
                    <Text style={styles.metaLabel}>İnceleme Gerekli</Text>
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
                            {alert.action_required ? 'Evet' : 'Hayır'}
                        </Text>
                    </View>
                </View>

                {dedupeKey ? (
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Dedupe Key</Text>
                        <Text style={styles.metaValueMono}>{dedupeKey}</Text>
                    </View>
                ) : null}

                {alert.log_ids && alert.log_ids.length > 0 && (
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>İlgili Loglar</Text>
                        <Text style={styles.metaValue}>{alert.log_ids.length} log</Text>
                    </View>
                )}
            </View>

            {/* Chat Butonu */}
            <TouchableOpacity
                style={styles.chatButton}
                onPress={() =>
                    navigation.navigate('Chat', {
                        alertId: alert.id,
                        alertTitle: title,
                        followUpQuestions,
                    })
                }
            >
                <Ionicons name="chatbubbles" size={22} color="#fff" />
                <Text style={styles.chatButtonText}>Bu Alert Hakkında Sohbet Et</Text>
            </TouchableOpacity>

            {/* Takip Soruları Preview */}
            {followUpQuestions.length > 0 && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Önerilen Sorular</Text>
                    {followUpQuestions.map((q, i) => (
                        <TouchableOpacity
                            key={i}
                            style={styles.questionChip}
                            onPress={() =>
                                navigation.navigate('Chat', {
                                    alertId: alert.id,
                                    alertTitle: title,
                                    followUpQuestions,
                                    initialMessage: q,
                                })
                            }
                        >
                            <Ionicons name="help-circle-outline" size={14} color="#6C63FF" />
                            <Text style={styles.questionText}>{q}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            )}

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
        fontSize: 18,
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
    titleText: {
        color: '#e0e0e0',
        fontSize: 15,
        fontWeight: '600',
        marginTop: 12,
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
        marginBottom: 12,
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
        fontSize: 13,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginBottom: 8,
    },
    summaryText: {
        color: '#e0e0e0',
        fontSize: 15,
        lineHeight: 22,
        fontWeight: '500',
    },
    bodyText: {
        color: '#ccc',
        fontSize: 14,
        lineHeight: 22,
    },
    listItem: {
        flexDirection: 'row',
        gap: 8,
        marginBottom: 6,
        alignItems: 'flex-start',
    },
    listBullet: {
        color: '#6C63FF',
        fontSize: 14,
        fontWeight: '700',
        width: 20,
    },
    listText: {
        color: '#ccc',
        fontSize: 14,
        lineHeight: 20,
        flex: 1,
    },
    codeHint: {
        backgroundColor: '#0d0d0d',
        borderRadius: 8,
        padding: 10,
        marginBottom: 6,
        borderLeftWidth: 3,
        borderLeftColor: '#00BCD4',
    },
    codeHintText: {
        color: '#aaa',
        fontSize: 12,
        fontFamily: 'monospace',
    },
    tagsRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 6,
    },
    tag: {
        backgroundColor: '#6C63FF20',
        borderRadius: 6,
        paddingHorizontal: 10,
        paddingVertical: 4,
    },
    tagText: {
        color: '#6C63FF',
        fontSize: 11,
        fontWeight: '600',
    },
    assumptionText: {
        color: '#999',
        fontSize: 13,
        lineHeight: 20,
        fontStyle: 'italic',
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
    chatButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        backgroundColor: '#6C63FF',
        marginHorizontal: 16,
        marginBottom: 12,
        borderRadius: 12,
        paddingVertical: 14,
    },
    chatButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '700',
    },
    questionChip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: '#6C63FF10',
        borderRadius: 8,
        padding: 12,
        marginBottom: 6,
        borderWidth: 1,
        borderColor: '#6C63FF30',
    },
    questionText: {
        color: '#ccc',
        fontSize: 13,
        flex: 1,
    },
});
