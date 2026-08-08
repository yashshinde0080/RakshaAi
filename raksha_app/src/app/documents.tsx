import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  TextInput,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import {
  deleteDocument,
  errMsg,
  listDocuments,
  queryDocuments,
  uploadDocument,
} from '@/api';
import type { DocInfo, QueryResult } from '@/types';

export default function DocumentsScreen() {
  const theme = useTheme();
  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [querying, setQuerying] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await listDocuments();
      setDocuments(res.documents ?? []);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pickAndUpload = async () => {
    const picked = await DocumentPicker.getDocumentAsync({
      type: ['text/plain', 'application/pdf'],
      copyToCacheDirectory: true,
    });
    if (picked.canceled || !picked.assets?.[0]) return;

    const file = picked.assets[0];
    const name = file.name.toLowerCase();
    if (!name.endsWith('.txt') && !name.endsWith('.pdf')) {
      Alert.alert('Unsupported file', 'Only .txt and .pdf files are accepted.');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await uploadDocument({
        uri: file.uri,
        name: file.name,
        type: file.mimeType ?? (name.endsWith('.pdf') ? 'application/pdf' : 'text/plain'),
      });
      await load();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setUploading(false);
    }
  };

  const confirmDelete = (doc: DocInfo) => {
    Alert.alert('Delete document', `Delete "${doc.filename}"? This cannot be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteDocument(doc.id);
            await load();
          } catch (e) {
            setError(errMsg(e));
          }
        },
      },
    ]);
  };

  const runQuery = async () => {
    if (!query.trim()) return;
    setQuerying(true);
    setQueryResult(null);
    try {
      setQueryResult(await queryDocuments(query.trim()));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setQuerying(false);
    }
  };

  const header = (
    <ThemedView style={styles.header}>
      <ThemedText type="subtitle">Documents</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        Upload documents for RAG, then ask questions about them.
      </ThemedText>
      {error && <ErrorBanner message={error} />}

      <Pressable
        onPress={pickAndUpload}
        disabled={uploading}
        style={({ pressed }) => [
          styles.uploadButton,
          { backgroundColor: theme.backgroundSelected },
          (pressed || uploading) && styles.pressed,
        ]}>
        {uploading ? (
          <ActivityIndicator size="small" />
        ) : (
          <ThemedText type="smallBold">⬆ Upload .txt / .pdf</ThemedText>
        )}
      </Pressable>

      <ThemedView type="backgroundElement" style={styles.card}>
        <ThemedText type="smallBold" style={styles.cardTitle}>
          Query documents
        </ThemedText>
        <TextInput
          style={[styles.input, { color: theme.text, backgroundColor: theme.background }]}
          placeholder="Enter your question…"
          placeholderTextColor={theme.textSecondary}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={runQuery}
          returnKeyType="search"
          editable={!querying}
        />
        <Pressable
          onPress={runQuery}
          disabled={querying || !query.trim()}
          style={({ pressed }) => [
            styles.actionButton,
            { backgroundColor: theme.backgroundSelected },
            (pressed || querying || !query.trim()) && styles.pressed,
          ]}>
          <ThemedText type="smallBold">{querying ? 'Searching…' : 'Search'}</ThemedText>
        </Pressable>

        {queryResult && (
          <ThemedView style={styles.queryResult}>
            {queryResult.generated_response ? (
              <ThemedText type="small">{queryResult.generated_response}</ThemedText>
            ) : (
              <ThemedText type="small" themeColor="textSecondary">
                No generated answer (no model loaded) — showing retrieved chunks.
              </ThemedText>
            )}
            {queryResult.results?.map((r, i) => (
              <ThemedView key={i} type="backgroundSelected" style={styles.resultRow}>
                <ThemedText type="small">{r.text}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  Score: {(r.score * 100).toFixed(1)}%
                </ThemedText>
              </ThemedView>
            ))}
          </ThemedView>
        )}
      </ThemedView>
    </ThemedView>
  );

  return (
    <FlatList
      data={documents}
      keyExtractor={(d) => d.id}
      ListHeaderComponent={header}
      renderItem={({ item }) => (
        <ThemedView type="backgroundElement" style={styles.docRow}>
          <ThemedView style={styles.docInfo}>
            <ThemedText type="smallBold" numberOfLines={1}>
              📄 {item.filename}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {item.chunks} chunks · {new Date(item.created_at).toLocaleDateString()}
            </ThemedText>
          </ThemedView>
          <Pressable
            onPress={() => confirmDelete(item)}
            hitSlop={8}
            style={({ pressed }) => pressed && styles.pressed}>
            <ThemedText type="small" style={{ color: theme.error }}>
              Delete
            </ThemedText>
          </Pressable>
        </ThemedView>
      )}
      ListEmptyComponent={
        !loading ? (
          <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
            No documents uploaded yet. Upload a PDF or TXT to get started.
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
  uploadButton: {
    borderRadius: Spacing.three,
    paddingVertical: Spacing.two,
    alignItems: 'center',
    minHeight: 40,
    justifyContent: 'center',
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  input: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 15,
  },
  actionButton: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.two,
    alignItems: 'center',
  },
  queryResult: {
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  resultRow: {
    borderRadius: Spacing.two,
    padding: Spacing.two,
    gap: Spacing.one,
  },
  docRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
    borderRadius: Spacing.three,
    padding: Spacing.three,
  },
  docInfo: {
    flex: 1,
    gap: Spacing.half,
  },
  empty: {
    textAlign: 'center',
    marginTop: Spacing.five,
  },
  pressed: {
    opacity: 0.5,
  },
});
