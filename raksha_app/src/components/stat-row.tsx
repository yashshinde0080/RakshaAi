import { StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <ThemedView style={styles.row}>
      <ThemedText type="small" themeColor="textSecondary" style={styles.label}>
        {label}
      </ThemedText>
      <ThemedText type="small" style={styles.value} numberOfLines={1}>
        {value}
      </ThemedText>
    </ThemedView>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  const theme = useTheme();
  return (
    <ThemedView style={[styles.banner, { borderColor: theme.error }]}>
      <ThemedText type="small" style={{ color: theme.error }}>
        ⚠ {message}
      </ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.one,
    gap: Spacing.three,
  },
  label: {
    flexShrink: 0,
  },
  value: {
    flexShrink: 1,
    textAlign: 'right',
  },
  banner: {
    borderWidth: 1,
    borderRadius: Spacing.three,
    padding: Spacing.three,
    marginBottom: Spacing.three,
  },
});
