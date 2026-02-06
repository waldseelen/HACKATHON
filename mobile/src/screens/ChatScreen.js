import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    FlatList,
    KeyboardAvoidingView,
    Platform,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from 'react-native';
import { fetchChatHistory, sendChatMessage } from '../services/api';

export default function ChatScreen({ route }) {
    const { alertId, alertTitle, followUpQuestions = [], initialMessage } = route.params || {};

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const flatListRef = useRef(null);

    // Geçmişi yükle
    useEffect(() => {
        (async () => {
            try {
                const history = await fetchChatHistory(alertId);
                setMessages(history.map((m, i) => ({
                    id: m.id || `h_${i}`,
                    role: m.role,
                    content: m.content,
                })));
            } catch {
                // İlk sohbet — boş başla
            } finally {
                setLoadingHistory(false);
            }
        })();
    }, [alertId]);

    // initialMessage varsa otomatik gönder
    useEffect(() => {
        if (initialMessage && !loadingHistory) {
            handleSend(initialMessage);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [loadingHistory]);

    const handleSend = useCallback(async (overrideMsg) => {
        const text = overrideMsg || input.trim();
        if (!text || sending) return;

        const userMsg = { id: `u_${Date.now()}`, role: 'user', content: text };
        setMessages((prev) => [...prev, userMsg]);
        setInput('');
        setSending(true);

        try {
            const history = messages.map((m) => ({ role: m.role, content: m.content }));
            const result = await sendChatMessage(alertId, text, history);
            const assistantMsg = {
                id: `a_${Date.now()}`,
                role: 'assistant',
                content: result.reply,
            };
            setMessages((prev) => [...prev, assistantMsg]);
        } catch (err) {
            const errorMsg = {
                id: `e_${Date.now()}`,
                role: 'assistant',
                content: `Hata: ${err.message}. Lütfen tekrar deneyin.`,
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setSending(false);
        }
    }, [input, sending, messages, alertId]);

    const renderMessage = ({ item }) => {
        const isUser = item.role === 'user';
        return (
            <View style={[styles.msgRow, isUser && styles.msgRowUser]}>
                {!isUser && (
                    <View style={styles.avatarAi}>
                        <Ionicons name="analytics" size={16} color="#6C63FF" />
                    </View>
                )}
                <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAi]}>
                    <Text style={[styles.msgText, isUser && styles.msgTextUser]}>
                        {item.content}
                    </Text>
                </View>
            </View>
        );
    };

    const renderSuggestions = () => {
        if (messages.length > 0 || followUpQuestions.length === 0) return null;
        return (
            <View style={styles.suggestionsContainer}>
                <Text style={styles.suggestionsTitle}>Önerilen Sorular</Text>
                {followUpQuestions.map((q, i) => (
                    <TouchableOpacity
                        key={i}
                        style={styles.suggestionChip}
                        onPress={() => handleSend(q)}
                    >
                        <Ionicons name="chatbubble-ellipses-outline" size={14} color="#6C63FF" />
                        <Text style={styles.suggestionText}>{q}</Text>
                    </TouchableOpacity>
                ))}
            </View>
        );
    };

    if (loadingHistory) {
        return (
            <View style={styles.centered}>
                <ActivityIndicator size="large" color="#6C63FF" />
            </View>
        );
    }

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            keyboardVerticalOffset={90}
        >
            {/* Alert başlığı */}
            <View style={styles.alertBanner}>
                <Ionicons name="information-circle" size={16} color="#6C63FF" />
                <Text style={styles.alertBannerText} numberOfLines={1}>
                    {alertTitle || 'Alert Sohbeti'}
                </Text>
            </View>

            <FlatList
                ref={flatListRef}
                data={messages}
                keyExtractor={(item) => item.id}
                renderItem={renderMessage}
                ListEmptyComponent={renderSuggestions}
                contentContainerStyle={styles.messagesList}
                onContentSizeChange={() =>
                    flatListRef.current?.scrollToEnd({ animated: true })
                }
            />

            {/* Yazıyor göstergesi */}
            {sending && (
                <View style={styles.typingIndicator}>
                    <ActivityIndicator size="small" color="#6C63FF" />
                    <Text style={styles.typingText}>AI düşünüyor…</Text>
                </View>
            )}

            {/* Giriş alanı */}
            <View style={styles.inputBar}>
                <TextInput
                    style={styles.textInput}
                    value={input}
                    onChangeText={setInput}
                    placeholder="Soru sorun…"
                    placeholderTextColor="#555"
                    multiline
                    maxLength={1000}
                    returnKeyType="send"
                    onSubmitEditing={() => handleSend()}
                    blurOnSubmit={false}
                />
                <TouchableOpacity
                    style={[styles.sendButton, (!input.trim() || sending) && styles.sendButtonDisabled]}
                    onPress={() => handleSend()}
                    disabled={!input.trim() || sending}
                >
                    <Ionicons name="send" size={20} color="#fff" />
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0a0a0a',
    },
    centered: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#0a0a0a',
    },
    alertBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: '#1a1a1a',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderBottomWidth: 1,
        borderBottomColor: '#2a2a2a',
    },
    alertBannerText: {
        color: '#ccc',
        fontSize: 13,
        fontWeight: '600',
        flex: 1,
    },
    messagesList: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        flexGrow: 1,
    },
    msgRow: {
        flexDirection: 'row',
        marginBottom: 10,
        alignItems: 'flex-end',
    },
    msgRowUser: {
        justifyContent: 'flex-end',
    },
    avatarAi: {
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: '#6C63FF20',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 8,
    },
    bubble: {
        maxWidth: '78%',
        borderRadius: 16,
        padding: 12,
    },
    bubbleUser: {
        backgroundColor: '#6C63FF',
        borderBottomRightRadius: 4,
    },
    bubbleAi: {
        backgroundColor: '#1a1a1a',
        borderBottomLeftRadius: 4,
        borderWidth: 1,
        borderColor: '#2a2a2a',
    },
    msgText: {
        color: '#e0e0e0',
        fontSize: 14,
        lineHeight: 20,
    },
    msgTextUser: {
        color: '#fff',
    },
    typingIndicator: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 16,
        paddingVertical: 6,
    },
    typingText: {
        color: '#888',
        fontSize: 12,
    },
    inputBar: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        padding: 8,
        paddingBottom: Platform.OS === 'ios' ? 24 : 8,
        borderTopWidth: 1,
        borderTopColor: '#2a2a2a',
        backgroundColor: '#111',
    },
    textInput: {
        flex: 1,
        backgroundColor: '#1a1a1a',
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 10,
        color: '#fff',
        fontSize: 15,
        maxHeight: 100,
        borderWidth: 1,
        borderColor: '#2a2a2a',
    },
    sendButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#6C63FF',
        justifyContent: 'center',
        alignItems: 'center',
        marginLeft: 8,
    },
    sendButtonDisabled: {
        opacity: 0.4,
    },
    suggestionsContainer: {
        flex: 1,
        justifyContent: 'center',
        paddingHorizontal: 16,
        paddingVertical: 32,
    },
    suggestionsTitle: {
        color: '#888',
        fontSize: 14,
        fontWeight: '600',
        textAlign: 'center',
        marginBottom: 16,
    },
    suggestionChip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        backgroundColor: '#1a1a1a',
        borderRadius: 12,
        padding: 14,
        marginBottom: 8,
        borderWidth: 1,
        borderColor: '#6C63FF30',
    },
    suggestionText: {
        color: '#ccc',
        fontSize: 14,
        flex: 1,
    },
});
