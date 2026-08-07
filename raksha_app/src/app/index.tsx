import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useChat } from '@/hooks/useChat';
import { useTheme } from '@/hooks/use-theme';
import type { Message } from '@/types';

export default function ChatScreen() {
  const { messages, isLoading, enableThinking, setEnableThinking, send, clear } = useChat();
  const theme = useTheme();
  const [draft, setDraft] = useState('');
  const [expanded, setExpanded] = useState<number | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const submit = () => {
    send(draft);
    setDraft('');
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <ThemedView style={styles.header}>
          <ThemedText type="smallBold">Raksha AI</ThemedText>
          <ThemedView style={styles.headerRight}>
            <ThemedText type="small" themeColor="textSecondary">
              Thinking
            </ThemedText>
            <Switch
              value={enableThinking}
              onValueChange={setEnableThinking}
              trackColor={{ true: theme.textSecondary }}
            />
            <Pressable onPress={clear} hitSlop={8} style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" themeColor="textSecondary">
                Clear
              </ThemedText>
            </Pressable>
          </ThemedView>
        </ThemedView>

        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.messages}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}>
          {messages.length === 0 && (
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              Ask anything — replies stream from your local model server.
            </ThemedText>
          )}
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              message={m}
              expanded={expanded === i}
              onToggleReasoning={() => setExpanded(expanded === i ? null : i)}
            />
          ))}
          {isLoading &&
            !messages[messages.length - 1]?.content &&
            !messages[messages.length - 1]?.reasoning && (
              <ThemedView type="backgroundElement" style={styles.bubbleAssistant}>
                <ActivityIndicator size="small" />
              </ThemedView>
            )}
        </ScrollView>

        <ThemedView style={styles.inputRow}>
          <TextInput
            style={[styles.input, { color: theme.text, backgroundColor: theme.backgroundElement }]}
            placeholder="Message…"
            placeholderTextColor={theme.textSecondary}
            value={draft}
            onChangeText={setDraft}
            onSubmitEditing={submit}
            returnKeyType="send"
            editable={!isLoading}
          />
          <Pressable
            onPress={submit}
            disabled={isLoading || !draft.trim()}
            style={({ pressed }) => [
              styles.sendButton,
              { backgroundColor: theme.backgroundSelected },
              (pressed || isLoading || !draft.trim()) && styles.pressed,
            ]}>
            <ThemedText type="smallBold">Send</ThemedText>
          </Pressable>
        </ThemedView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

function MessageBubble({
  message,
  expanded,
  onToggleReasoning,
}: {
  message: Message;
  expanded: boolean;
  onToggleReasoning: () => void;
}) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <ThemedView type="backgroundSelected" style={[styles.bubble, styles.bubbleUser]}>
        <ThemedText>{message.content}</ThemedText>
      </ThemedView>
    );
  }

  return (
    <ThemedView type="backgroundElement" style={[styles.bubble, styles.bubbleAssistant]}>
      {!!message.reasoning && (
        <Pressable onPress={onToggleReasoning} hitSlop={6}>
          <ThemedText type="small" themeColor="textSecondary">
            {expanded ? '▾' : '▸'} Thinking
          </ThemedText>
        </Pressable>
      )}
      {expanded && !!message.reasoning && (
        <ThemedText type="small" themeColor="textSecondary" style={styles.reasoning}>
          {message.reasoning}
        </ThemedText>
      )}
      {!!message.content && <ThemedText>{message.content}</ThemedText>}
      {!!message.sources?.length && (
        <ThemedView style={styles.sources}>
          {message.sources.map((s) => (
            <ThemedView key={s.filename} type="backgroundSelected" style={styles.chip}>
              <ThemedText type="small" themeColor="textSecondary">
                📄 {s.filename}
              </ThemedText>
            </ThemedView>
          ))}
        </ThemedView>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#8888',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  messages: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  empty: {
    textAlign: 'center',
    marginTop: Spacing.five,
  },
  bubble: {
    maxWidth: '92%',
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  bubbleUser: {
    alignSelf: 'flex-end',
  },
  bubbleAssistant: {
    alignSelf: 'flex-start',
  },
  reasoning: {
    borderLeftWidth: 2,
    borderLeftColor: '#8888',
    paddingLeft: Spacing.two,
  },
  sources: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
    marginTop: Spacing.one,
  },
  chip: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: BottomTabInset,
  },
  input: {
    flex: 1,
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
  },
  sendButton: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
  },
  pressed: {
    opacity: 0.5,
  },
});
