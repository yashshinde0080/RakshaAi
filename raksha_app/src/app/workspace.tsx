import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Pressable, RefreshControl, StyleSheet } from 'react-native';

import { ErrorBanner, StatRow } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useServer } from '@/hooks/useServer';
import { useTheme } from '@/hooks/use-theme';
import {
  deleteWorkspace,
  errMsg,
  listWorkspaces,
  loadModel,
  loadWorkspace,
  saveWorkspace,
} from '@/api';
import type { WorkspaceSnapshot } from '@/types';

export default function WorkspaceScreen() {
  const theme = useTheme();
  const { status, refresh } = useServer();
  const [snapshots, setSnapshots] = useState<WorkspaceSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await listWorkspaces();
      setSnapshots(res.snapshots ?? []);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await saveWorkspace();
      await load();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  const restore = async (snap: WorkspaceSnapshot) => {
    setBusyId(snap.id);
    setError(null);
    try {
      const s = await loadWorkspace(snap.id);
      if (s.model) {
        await loadModel(s.model, s.mode || 'auto');
        await refresh();
      }
      await load();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusyId(null);
    }
  };

  const confirmDelete = (snap: WorkspaceSnapshot) => {
    Alert.alert('Delete snapshot', 'Delete this snapshot? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteWorkspace(snap.id);
            await load();
          } catch (e) {
            setError(errMsg(e));
          }
        },
      },
    ]);
  };

  const header = (
    <ThemedView style={styles.header}>
      <ThemedText type="subtitle">Workspace</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        Save and restore your work sessions
      </ThemedText>
      {error && <ErrorBanner message={error} />}

      <ThemedView type="backgroundElement" style={styles.card}>
        <ThemedText type="smallBold" style={styles.cardTitle}>
          Current session
        </ThemedText>
        <StatRow label="Model" value={status?.current_model ?? 'none'} />
        <StatRow label="Mode" value={status?.current_mode ?? 'auto'} />
        <Pressable
          onPress={save}
          disabled={saving}
          style={({ pressed }) => [
            styles.actionButton,
            { backgroundColor: theme.backgroundSelected },
            (pressed || saving) && styles.pressed,
          ]}>
          {saving ? (
            <ActivityIndicator size="small" />
          ) : (
            <ThemedText type="smallBold">Save Snapshot</ThemedText>
          )}
        </Pressable>
      </ThemedView>
    </ThemedView>
  );

  return (
    <FlatList
      data={snapshots}
      keyExtractor={(s) => s.id}
      ListHeaderComponent={header}
      renderItem={({ item }) => (
        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold" numberOfLines={1}>
            {item.model || 'no model'}
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {new Date(item.timestamp * 1000).toLocaleString()} · {item.mode || 'auto'}
          </ThemedText>
          <ThemedView style={styles.row}>
            <Pressable
              onPress={() => restore(item)}
              disabled={busyId === item.id}
              style={({ pressed }) => [
                styles.actionButton,
                { backgroundColor: theme.backgroundSelected, flex: 1 },
                (pressed || busyId === item.id) && styles.pressed,
              ]}>
              {busyId === item.id ? (
                <ActivityIndicator size="small" />
              ) : (
                <ThemedText type="smallBold">Load</ThemedText>
              )}
            </Pressable>
            <Pressable
              onPress={() => confirmDelete(item)}
              hitSlop={8}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" style={{ color: theme.error }}>
                Delete
              </ThemedText>
            </Pressable>
          </ThemedView>
        </ThemedView>
      )}
      ListEmptyComponent={
        !loading ? (
          <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
            No snapshots saved yet. Save your current workspace to restore it later.
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
    gap: Spacing.three,
    marginBottom: Spacing.two,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    marginTop: Spacing.one,
  },
  actionButton: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.two,
    alignItems: 'center',
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
