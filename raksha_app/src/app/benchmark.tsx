import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';

import { ErrorBanner, StatRow } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useServer } from '@/hooks/useServer';
import { useTheme } from '@/hooks/use-theme';
import { compareModes, errMsg, runBenchmark } from '@/api';
import type { BenchmarkResult, CompareResponse } from '@/types';

export default function BenchmarkScreen() {
  const { status, loading } = useServer();
  const theme = useTheme();
  const router = useRouter();

  const [iterations, setIterations] = useState(3);
  const [maxTokens, setMaxTokens] = useState(100);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading) {
    return (
      <ScrollView contentContainerStyle={styles.gate}>
        <ActivityIndicator size="small" />
      </ScrollView>
    );
  }

  if (!status?.model_loaded) {
    return (
      <ScrollView contentContainerStyle={styles.gate}>
        <ThemedView type="backgroundElement" style={styles.gateCard}>
          <ThemedText type="small" themeColor="textSecondary">
            No model is loaded. Load a model first to run benchmarks.
          </ThemedText>
          <Pressable
            onPress={() => router.push('/models')}
            style={({ pressed }) => [
              styles.actionButton,
              { backgroundColor: theme.backgroundSelected },
              pressed && styles.pressed,
            ]}>
            <ThemedText type="smallBold">Go to Models</ThemedText>
          </Pressable>
        </ThemedView>
      </ScrollView>
    );
  }

  const run = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await runBenchmark(iterations, maxTokens));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setRunning(false);
    }
  };

  const compare = async () => {
    setComparing(true);
    setError(null);
    try {
      setCompareResult(await compareModes());
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setComparing(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.list}>
      <ThemedText type="subtitle">Benchmark</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        Model: {status.current_model} · Mode: {status.current_mode}
      </ThemedText>
      {error && <ErrorBanner message={error} />}

      <ThemedView type="backgroundElement" style={styles.card}>
        <ThemedText type="smallBold" style={styles.cardTitle}>
          Configuration
        </ThemedText>
        <Stepper label="Iterations" value={iterations} min={1} max={10} onChange={setIterations} />
        <Stepper label="Max tokens" value={maxTokens} min={10} max={500} step={10} onChange={setMaxTokens} />
        <Pressable
          onPress={run}
          disabled={running}
          style={({ pressed }) => [
            styles.actionButton,
            { backgroundColor: theme.backgroundSelected },
            (pressed || running) && styles.pressed,
          ]}>
          {running ? (
            <ActivityIndicator size="small" />
          ) : (
            <ThemedText type="smallBold">Run Benchmark</ThemedText>
          )}
        </Pressable>
      </ThemedView>

      <ThemedView type="backgroundElement" style={styles.card}>
        <ThemedText type="smallBold" style={styles.cardTitle}>
          Mode comparison
        </ThemedText>
        <Pressable
          onPress={compare}
          disabled={comparing}
          style={({ pressed }) => [
            styles.actionButton,
            { backgroundColor: theme.backgroundSelected },
            (pressed || comparing) && styles.pressed,
          ]}>
          {comparing ? (
            <ActivityIndicator size="small" />
          ) : (
            <ThemedText type="smallBold">Compare fullram vs layerstream</ThemedText>
          )}
        </Pressable>
        {compareResult &&
          Object.entries(compareResult.results ?? {}).map(([mode, data]) => (
            <ThemedView key={mode} type="background" style={styles.subCard}>
              <ThemedText type="smallBold">{mode}</ThemedText>
              {data.available === false ? (
                <ThemedText type="small" themeColor="textSecondary">
                  {data.reason}
                </ThemedText>
              ) : (
                <>
                  <StatRow label="TPS" value={data.tps?.toFixed(2) ?? '—'} />
                  <StatRow label="Time" value={`${data.time_s?.toFixed(2)}s`} />
                  <StatRow label="Tokens" value={String(data.tokens ?? '—')} />
                  <StatRow label="RAM" value={`${data.ram_gb?.toFixed(2)} GB`} />
                </>
              )}
            </ThemedView>
          ))}
      </ThemedView>

      {result && (
        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold" style={styles.cardTitle}>
            Results — {result.iterations} iterations
          </ThemedText>
          {result.runs.map((run) => (
            <ThemedView key={run.iteration} type="background" style={styles.subCard}>
              <StatRow label={`Iteration ${run.iteration}`} value={`${run.tokens_per_second.toFixed(2)} tok/s`} />
              <StatRow label="Tokens" value={String(run.tokens)} />
              <StatRow label="Time" value={`${run.time_seconds.toFixed(3)}s`} />
            </ThemedView>
          ))}
          <ThemedView style={styles.summary}>
            <StatRow label="Total tokens" value={String(result.summary.total_tokens)} />
            <StatRow label="Total time" value={`${result.summary.total_time_seconds.toFixed(2)}s`} />
            <StatRow
              label="Avg TPS"
              value={result.summary.average_tokens_per_second.toFixed(2)}
            />
            <StatRow label="Peak RAM" value={`${result.summary.peak_ram_gb.toFixed(2)} GB`} />
          </ThemedView>
        </ThemedView>
      )}
    </ScrollView>
  );
}

function Stepper({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  const theme = useTheme();
  return (
    <ThemedView style={styles.stepperRow}>
      <ThemedText type="small" style={styles.stepperLabel}>
        {label}
      </ThemedText>
      <ThemedView style={styles.stepper}>
        <Pressable
          onPress={() => onChange(Math.max(min, value - step))}
          hitSlop={8}
          style={({ pressed }) => [styles.stepButton, { backgroundColor: theme.background }, pressed && styles.pressed]}>
          <ThemedText type="smallBold">−</ThemedText>
        </Pressable>
        <ThemedText type="smallBold" style={styles.stepperValue}>
          {value}
        </ThemedText>
        <Pressable
          onPress={() => onChange(Math.min(max, value + step))}
          hitSlop={8}
          style={({ pressed }) => [styles.stepButton, { backgroundColor: theme.background }, pressed && styles.pressed]}>
          <ThemedText type="smallBold">+</ThemedText>
        </Pressable>
      </ThemedView>
    </ThemedView>
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
  gateCard: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  subCard: {
    borderRadius: Spacing.two,
    padding: Spacing.two,
    gap: Spacing.one,
  },
  summary: {
    marginTop: Spacing.one,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#8888',
    paddingTop: Spacing.two,
  },
  actionButton: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.two,
    alignItems: 'center',
    marginTop: Spacing.one,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: Spacing.one,
  },
  stepperLabel: {
    flexShrink: 1,
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  stepButton: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  stepperValue: {
    minWidth: 36,
    textAlign: 'center',
  },
  pressed: {
    opacity: 0.5,
  },
});
