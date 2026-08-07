import { RefreshControl, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorBanner, StatRow } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useServer } from '@/hooks/useServer';
import { useTheme } from '@/hooks/use-theme';

export default function SystemScreen() {
  const { status, hardware, loading, error, refresh } = useServer();
  const theme = useTheme();

  return (
    <SafeAreaView style={styles.flex} edges={['top']}>
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={theme.textSecondary} />
        }>
        <ThemedText type="subtitle">System</ThemedText>
        {error && <ErrorBanner message={error} />}

        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold" style={styles.cardTitle}>
            Server
          </ThemedText>
          <StatRow
            label="Model"
            value={status?.model_loaded ? (status.current_model ?? '—') : 'None'}
          />
          <StatRow label="Mode" value={status?.current_mode ?? '—'} />
          <StatRow label="Task" value={status?.task_type ?? '—'} />
          <StatRow
            label="RAM"
            value={
              status ? `${status.ram_used_gb.toFixed(1)} / ${status.ram_total_gb.toFixed(1)} GB` : '—'
            }
          />
          <StatRow
            label="Disk free"
            value={status ? `${status.disk_free_gb.toFixed(0)} / ${status.disk_total_gb.toFixed(0)} GB` : '—'}
          />
        </ThemedView>

        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold" style={styles.cardTitle}>
            Hardware
          </ThemedText>
          <StatRow label="CPU" value={hardware?.cpu_name ?? '—'} />
          <StatRow
            label="Cores"
            value={hardware ? `${hardware.cpu_cores} / ${hardware.cpu_threads} threads` : '—'}
          />
          <StatRow label="RAM" value={hardware ? `${hardware.ram_total_gb.toFixed(0)} GB` : '—'} />
          <StatRow label="GPU" value={hardware?.gpu_name ?? 'None'} />
          <StatRow
            label="GPU VRAM"
            value={hardware?.gpu_vram_gb ? `${hardware.gpu_vram_gb.toFixed(0)} GB` : '—'}
          />
          <StatRow label="Disk" value={hardware?.disk_type ?? '—'} />
        </ThemedView>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  list: {
    padding: Spacing.three,
    paddingBottom: BottomTabInset,
    gap: Spacing.three,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
});
