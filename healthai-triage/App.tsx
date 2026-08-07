import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';

import { Disclaimer } from './src/components/Disclaimer';
import { HistoryScreen } from './src/screens/HistoryScreen';
import { ResultScreen } from './src/screens/ResultScreen';
import { TriageFormScreen } from './src/screens/TriageFormScreen';
import { capRecords, createRecord, TriageRecord } from './src/storage/record';
import { loadHistory, persistHistory } from './src/storage/history';
import { spacing, useThemeColors } from './src/theme';
import { TriageInput, TriageResult } from './src/types';

type Screen =
  | { name: 'form' }
  | { name: 'result'; result: TriageResult }
  | { name: 'history' };

export default function App() {
  const c = useThemeColors();
  const [screen, setScreen] = useState<Screen>({ name: 'form' });
  const [records, setRecords] = useState<TriageRecord[]>([]);

  // Load persisted history once on launch. Fire-and-forget; UI renders empty
  // list until it resolves, which is invisible on fast local storage.
  useEffect(() => {
    let cancelled = false;
    loadHistory().then((stored) => {
      if (!cancelled) {
        setRecords(stored);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleComplete(input: TriageInput, result: TriageResult) {
    const record = createRecord(input, result);
    setRecords((prev) => {
      const next = capRecords([record, ...prev]);
      persistHistory(next).catch(() => {
        // ponytail: local-only data; a failed write just loses this one
        // assessment, the in-memory list stays correct for the session.
      });
      return next;
    });
    setScreen({ name: 'result', result });
  }

  function handleDelete(id: string) {
    setRecords((prev) => {
      const next = prev.filter((r) => r.id !== id);
      persistHistory(next).catch(() => {});
      return next;
    });
  }

  function handleClearAll() {
    setRecords([]);
    persistHistory([]).catch(() => {});
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: c.background }]}>
      <StatusBar style="auto" />
      <Disclaimer />
      {screen.name === 'form' && (
        <TriageFormScreen onComplete={handleComplete} onOpenHistory={() => setScreen({ name: 'history' })} />
      )}
      {screen.name === 'result' && (
        <ResultScreen
          result={screen.result}
          onRestart={() => setScreen({ name: 'form' })}
          onOpenHistory={() => setScreen({ name: 'history' })}
        />
      )}
      {screen.name === 'history' && (
        <HistoryScreen
          records={records}
          onBack={() => setScreen({ name: 'form' })}
          onDelete={handleDelete}
          onClearAll={handleClearAll}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: spacing.md,
  },
});
