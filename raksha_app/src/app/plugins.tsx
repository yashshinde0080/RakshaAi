import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
} from 'react-native';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { disablePlugin, enablePlugin, errMsg, listPlugins } from '@/api';
import type { Plugin } from '@/types';

export default function PluginsScreen() {
  const theme = useTheme();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setPlugins(await listPlugins());
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (plugin: Plugin) => {
    setBusyId(plugin.id);
    setError(null);
    try {
      if (plugin.enabled) await disablePlugin(plugin.id);
      else await enablePlugin(plugin.id);
      await load();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <FlatList
      data={plugins}
      keyExtractor={(p) => p.id}
      ListHeaderComponent={
        <ThemedView style={styles.header}>
          <ThemedText type="subtitle">Plugins</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            Extend Raksha AI functionality
          </ThemedText>
          {error && <ErrorBanner message={error} />}
        </ThemedView>
      }
      renderItem={({ item }) => (
        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedView style={styles.topRow}>
            <ThemedText type="smallBold" style={styles.name} numberOfLines={1}>
              {item.name}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {item.builtin ? 'built-in' : 'user'} · v{item.version}
            </ThemedText>
          </ThemedView>
          <ThemedText type="small" themeColor="textSecondary">
            {item.description || 'No description'}
          </ThemedText>
          {item.actions.length > 0 && (
            <ThemedView style={styles.chips}>
              {item.actions.map((a) => (
                <ThemedView key={a} type="backgroundSelected" style={styles.chip}>
                  <ThemedText type="small">{a}</ThemedText>
                </ThemedView>
              ))}
            </ThemedView>
          )}
          <Pressable
            onPress={() => toggle(item)}
            disabled={busyId === item.id}
            style={({ pressed }) => [
              styles.toggle,
              { backgroundColor: item.enabled ? theme.backgroundSelected : theme.background },
              (pressed || busyId === item.id) && styles.pressed,
            ]}>
            {busyId === item.id ? (
              <ActivityIndicator size="small" />
            ) : (
              <ThemedText type="smallBold">
                {item.enabled ? 'Enabled — tap to disable' : 'Disabled — tap to enable'}
              </ThemedText>
            )}
          </Pressable>
        </ThemedView>
      )}
      ListEmptyComponent={
        !loading ? (
          <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
            No plugins found.
          </ThemedText>
        ) : null
      }
      contentContainerStyle={styles.list}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={load} tintColor={theme.textSecondary} />
      }
    />
  );
}

const styles = StyleSheet.create({
  list: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  header: {
    gap: Spacing.two,
    marginBottom: Spacing.two,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  name: {
    flexShrink: 1,
  },
  chips: {
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
  toggle: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.two,
    alignItems: 'center',
    marginTop: Spacing.two,
    minHeight: 38,
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
