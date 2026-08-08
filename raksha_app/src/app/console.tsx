import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
} from 'react-native';
import { useRouter } from 'expo-router';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useServer } from '@/hooks/useServer';
import { useTheme } from '@/hooks/use-theme';
import { errMsg, executeTask, getCurrentModel } from '@/api';
import type { MaskPrediction, TaskResult } from '@/types';

export default function ConsoleScreen() {
  const { status, loading, refresh } = useServer();
  const [taskType, setTaskType] = useState<string | null>(null);
  const [isGenerative, setIsGenerative] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cur = await getCurrentModel();
        if (cur.loaded) {
          setTaskType(cur.task_type);
          setIsGenerative(cur.is_generative || cur.task_type === 'causal_lm');
        }
      } catch {
        // fall back to status below
      }
    })();
  }, [status?.model_loaded]);

  if (loading) {
    return (
      <ThemedView style={styles.gateLoading}>
        <ActivityIndicator size="small" />
      </ThemedView>
    );
  }

  if (!status?.model_loaded) {
    return <NoModelGate onRefresh={refresh} />;
  }

  const activeTask = taskType || status.task_type || 'unknown';
  const activeGen = isGenerative || status.is_generative || activeTask === 'causal_lm';

  let module: React.ReactNode;
  if (activeGen) {
    module = <GenerativeModule />;
  } else if (
    activeTask.includes('classification') &&
    !activeTask.includes('vision') &&
    !activeTask.includes('audio') &&
    !activeTask.includes('image')
  ) {
    module = <ClassificationModule />;
  } else if (activeTask === 'question_answering') {
    module = <QAModule />;
  } else if (activeTask === 'masked_lm') {
    module = <MaskedLMModule />;
  } else if (activeTask === 'text_encoding') {
    module = <EmbeddingModule />;
  } else if (
    activeTask.includes('image') ||
    activeTask.includes('vision') ||
    activeTask.includes('audio') ||
    activeTask === 'object_detection'
  ) {
    module = (
      <ThemedText type="small" themeColor="textSecondary" style={styles.unsupported}>
        {activeTask} needs image/audio input, which this mobile build does not support yet.
        Execute it via the API instead.
      </ThemedText>
    );
  } else {
    module = (
      <ThemedText type="small" themeColor="textSecondary" style={styles.unsupported}>
        No UI module exists for task “{activeTask}” yet — you can still execute via the API.
      </ThemedText>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.list}>
      <ThemedView style={styles.statusRow}>
        <StatusChip label="Model" value={status.current_model ?? '—'} />
        <StatusChip label="Task" value={activeTask.replace(/_/g, ' ')} />
        <StatusChip label="Mode" value={status.current_mode ?? 'auto'} />
      </ThemedView>
      {module}
    </ScrollView>
  );
}

// ── Modules ─────────────────────────────────────────────────────────────────

function ModuleCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        {title}
      </ThemedText>
      {children}
    </ThemedView>
  );
}

function RunButton({
  label,
  loading,
  disabled,
  onPress,
}: {
  label: string;
  loading: boolean;
  disabled: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={loading || disabled}
      style={({ pressed }) => [
        styles.runButton,
        { backgroundColor: theme.backgroundSelected },
        (pressed || loading || disabled) && styles.pressed,
      ]}>
      {loading ? <ActivityIndicator size="small" /> : <ThemedText type="smallBold">{label}</ThemedText>}
    </Pressable>
  );
}

function TextField({
  value,
  onChangeText,
  placeholder,
  multiline,
  style,
}: {
  value: string;
  onChangeText: (t: string) => void;
  placeholder: string;
  multiline?: boolean;
  style?: object;
}) {
  const theme = useTheme();
  return (
    <TextInput
      style={[
        styles.textInput,
        multiline && styles.multiline,
        { color: theme.text, backgroundColor: theme.background },
        style,
      ]}
      placeholder={placeholder}
      placeholderTextColor={theme.textSecondary}
      value={value}
      onChangeText={onChangeText}
      multiline={multiline}
    />
  );
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <ThemedView type="backgroundSelected" style={styles.resultBox}>
      {children}
    </ThemedView>
  );
}

function GenerativeModule() {
  const router = useRouter();
  const theme = useTheme();
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        Generative chat model
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        This model is generative — chat with it on the Chat tab (with RAG + thinking toggles).
      </ThemedText>
      <Pressable
        onPress={() => router.push('/chat')}
        style={({ pressed }) => [
          styles.runButton,
          { backgroundColor: theme.backgroundSelected },
          pressed && styles.pressed,
        ]}>
        <ThemedText type="smallBold">Open Chat</ThemedText>
      </Pressable>
    </ThemedView>
  );
}

function ClassificationModule() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await executeTask({ prompt: input.trim() }));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ModuleCard title="Sequence Classification">
        <TextField
          value={input}
          onChangeText={setInput}
          placeholder="Enter text to classify…"
          multiline
        />
        <RunButton label="Classify" loading={loading} disabled={!input.trim()} onPress={run} />
      </ModuleCard>
      {error && <ErrorBanner message={error} />}
      {result && (
        <ResultBox>
          <ThemedText type="small" themeColor="textSecondary">
            Predicted label
          </ThemedText>
          <ThemedText type="subtitle">{result.output || '—'}</ThemedText>
          {result.confidence != null && (
            <ThemedText type="small" themeColor="textSecondary">
              Confidence: {(parseFloat(result.confidence) * 100).toFixed(1)}%
            </ThemedText>
          )}
        </ResultBox>
      )}
    </>
  );
}

function QAModule() {
  const [context, setContext] = useState('');
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await executeTask({ context: context.trim(), question: question.trim() }));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ModuleCard title="Extractive Question Answering">
        <TextField
          value={context}
          onChangeText={setContext}
          placeholder="Paste the reference context here…"
          multiline
        />
        <TextField value={question} onChangeText={setQuestion} placeholder="What would you like to know?" />
        <RunButton
          label="Extract Answer"
          loading={loading}
          disabled={!context.trim() || !question.trim()}
          onPress={run}
        />
      </ModuleCard>
      {error && <ErrorBanner message={error} />}
      {result && (
        <ResultBox>
          <ThemedText type="small" themeColor="textSecondary">
            Extracted answer
          </ThemedText>
          <ThemedText type="subtitle">{result.output || '—'}</ThemedText>
        </ResultBox>
      )}
    </>
  );
}

function EmbeddingModule() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await executeTask({ prompt: input.trim() }));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ModuleCard title="Text Encoding & Embeddings">
        <TextField
          value={input}
          onChangeText={setInput}
          placeholder="Enter text to convert to a vector embedding…"
          multiline
        />
        <RunButton label="Encode" loading={loading} disabled={!input.trim()} onPress={run} />
      </ModuleCard>
      {error && <ErrorBanner message={error} />}
      {result && (
        <ResultBox>
          <ThemedText type="small" themeColor="textSecondary">
            Tensor emission shape
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {JSON.stringify(result.shape ?? '[Hidden states emitted]')}
          </ThemedText>
        </ResultBox>
      )}
    </>
  );
}

function MaskedLMModule() {
  const theme = useTheme();
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await executeTask({ prompt: input.trim() }));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  };

  const insertMask = () => {
    setInput((prev) => (prev.trim() ? `${prev.trim()} [MASK]` : '[MASK]'));
  };

  const predictions = result?.predictions ?? [];

  return (
    <>
      <ModuleCard title="Masked Language Modeling">
        <TextField
          value={input}
          onChangeText={setInput}
          placeholder="The patient was diagnosed with [MASK] cancer."
          multiline
        />
        <ThemedView style={styles.maskRow}>
          <Pressable onPress={insertMask} hitSlop={8} style={({ pressed }) => pressed && styles.pressed}>
            <ThemedText type="small" themeColor="textSecondary">
              Insert [MASK]
            </ThemedText>
          </Pressable>
          <RunButton label="Predict" loading={loading} disabled={!input.trim()} onPress={run} />
        </ThemedView>
      </ModuleCard>
      {error && <ErrorBanner message={error} />}
      {result?.message && predictions.length === 0 && (
        <ResultBox>
          <ThemedText type="small" themeColor="textSecondary">
            Model response
          </ThemedText>
          <ThemedText type="small">{result.message}</ThemedText>
        </ResultBox>
      )}
      {predictions.length > 0 && (
        <ResultBox>
          <ThemedText type="smallBold" style={styles.cardTitle}>
            Fill-in-the-blank preview
          </ThemedText>
          <ThemedText type="small">
            {buildPreview(input, predictions)}
          </ThemedText>
        </ResultBox>
      )}
      {predictions.map((pred) => (
        <ModuleCard key={pred.position} title={`Mask position ${pred.position}`}>
          {pred.candidates.map((c, idx) => (
            <ThemedView key={c.token} style={styles.candidateRow}>
              <ThemedText
                type="small"
                style={[styles.candidateToken, idx === 0 && { fontWeight: 'bold' }]}
                numberOfLines={1}>
                {cleanToken(c.token)}
              </ThemedText>
              <ThemedView style={[styles.bar, { backgroundColor: theme.background }]}>
                <ThemedView
                  type="backgroundSelected"
                  style={{
                    width: `${Math.min(c.probability * 100, 100)}%`,
                    height: '100%',
                    borderRadius: 4,
                  }}
                />
              </ThemedView>
              <ThemedText type="small" themeColor="textSecondary" style={styles.candidateProb}>
                {(c.probability * 100).toFixed(1)}%
              </ThemedText>
            </ThemedView>
          ))}
        </ModuleCard>
      ))}
    </>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

/** BERT subword pieces carry a '##' prefix — strip it for display. */
function cleanToken(token: string): string {
  return token.replace(/^##+/, '');
}

/** Replace each [MASK] in order with the top candidate, left to right. */
function buildPreview(input: string, predictions: MaskPrediction[]): string {
  const parts = input.split('[MASK]');
  let out = parts[0] ?? '';
  predictions.forEach((pred, idx) => {
    const top = pred.candidates[0];
    out += top ? cleanToken(top.token) : '[MASK]';
    out += parts[idx + 1] ?? '';
  });
  return out;
}

function StatusChip({ label, value }: { label: string; value: string }) {
  return (
    <ThemedView type="backgroundElement" style={styles.chip}>
      <ThemedText type="small" themeColor="textSecondary">
        {label}: <ThemedText type="small">{value}</ThemedText>
      </ThemedText>
    </ThemedView>
  );
}

function NoModelGate({ onRefresh }: { onRefresh: () => void }) {
  const theme = useTheme();
  return (
    <ScrollView contentContainerStyle={styles.gate}>
      <ThemedView type="backgroundElement" style={styles.gateCard}>
        <ThemedText type="small" themeColor="textSecondary">
          No model is loaded. Load a model to begin task execution.
        </ThemedText>
        <Pressable
          onPress={onRefresh}
          style={({ pressed }) => [
            styles.runButton,
            { backgroundColor: theme.backgroundSelected },
            pressed && styles.pressed,
          ]}>
          <ThemedText type="smallBold">Refresh</ThemedText>
        </Pressable>
      </ThemedView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  list: {
    padding: Spacing.three,
    gap: Spacing.three,
  },
  gate: {
    flexGrow: 1,
    padding: Spacing.three,
    justifyContent: 'center',
  },
  gateLoading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gateCard: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  statusRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  chip: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  textInput: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 15,
  },
  multiline: {
    minHeight: 100,
    textAlignVertical: 'top',
  },
  runButton: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.two,
    alignItems: 'center',
    minHeight: 38,
    justifyContent: 'center',
  },
  resultBox: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  maskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  candidateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  candidateToken: {
    width: 110,
  },
  candidateProb: {
    width: 52,
    textAlign: 'right',
  },
  bar: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  unsupported: {
    textAlign: 'center',
    marginTop: Spacing.five,
    paddingHorizontal: Spacing.three,
  },
  pressed: {
    opacity: 0.5,
  },
});
