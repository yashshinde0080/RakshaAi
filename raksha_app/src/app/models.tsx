import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorBanner, StatRow } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useServer } from '@/hooks/useServer';
import { useTheme } from '@/hooks/use-theme';
import type { Model } from '@/types';

export default function ModelsScreen() {
  const { models, status, loading, busyId, error, refresh, load, unload } = useServer();
  const theme = useTheme();

  const header = (
    <ThemedView style={styles.header}>
      <ThemedText type="subtitle">Models</ThemedText>
      {error && <ErrorBanner message={error} />}
      <ThemedView type="backgroundElement" style={styles.statusCard}>
        {status?.model_loaded ? (
          <>
            <StatRow label="Loaded" value={status.current_model ?? ''} />
            <StatRow label="Mode" value={status.current_mode ?? ''} />
            <StatRow label="Task" value={status.task_type ?? ''} />
            <Pressable
              onPress={unload}
              disabled={busyId !== null}
              style={({ pressed }) => [
                styles.actionButton,
                { backgroundColor: theme.backgroundSelected },
                (pressed || busyId !== null) && styles.pressed,
              ]}>
              <ThemedText type="smallBold">Unload</ThemedText>
            </Pressable>
          </>
        ) : (
          <ThemedText type="small" themeColor="textSecondary">
            No model loaded
          </ThemedText>
        )}
      </ThemedView>
    </ThemedView>
  );

  const renderItem = ({ item }: { item: Model }) => {
    const isCurrent = status?.current_model === item.id;
    const busy = busyId === item.id;
    return (
      <ThemedView type="backgroundElement" style={styles.modelCard}>
        <ThemedView style={styles.modelTop}>
          <ThemedText type="smallBold" numberOfLines={1} style={styles.modelName}>
            {item.name}
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {item.quant} · {item.size_gb.toFixed(1)} GB
          </ThemedText>
        </ThemedView>
        <ThemedText type="small" themeColor="textSecondary">
          {item.family} · {item.parameters}
        </ThemedText>
        <ThemedView style={styles.modelBottom}>
          <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>
            {item.modes_supported?.join(' / ') || ''}
          </ThemedText>
          {isCurrent ? (
            <ThemedText type="smallBold">Active</ThemedText>
          ) : (
            <Pressable
              onPress={() => load(item.id)}
              disabled={busy || !item.downloaded}
              style={({ pressed }) => [
                styles.actionButton,
                { backgroundColor: theme.backgroundSelected },
                (pressed || busy || !item.downloaded) && styles.pressed,
              ]}>
              {busy ? (
                <ActivityIndicator size="small" />
              ) : (
                <ThemedText type="smallBold">
                  {item.downloaded ? 'Load' : 'Not downloaded'}
                </ThemedText>
              )}
            </Pressable>
          )}
        </ThemedView>
      </ThemedView>
    );
  };

  return (
    <SafeAreaView style={styles.flex} edges={['top']}>
      <FlatList
        data={models}
        keyExtractor={(m) => m.id}
        renderItem={renderItem}
        ListHeaderComponent={header}
        ListEmptyComponent={
          !loading ? (
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              No models installed. Pull models from the web dashboard, then refresh.
            </ThemedText>
          ) : null
        }
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={theme.textSecondary} />
        }
      />
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
  header: {
    gap: Spacing.three,
  },
  statusCard: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  modelCard: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  modelTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  modelName: {
    flexShrink: 1,
  },
  modelBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  actionButton: {
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
    minHeight: 32,
    justifyContent: 'center',
  },
  empty: {
    textAlign: 'center',
    marginTop: Spacing.five,
  },
  pressed: {
    opacity: 0.5,
  },
});
