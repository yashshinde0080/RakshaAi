import { StyleSheet, Text, View } from 'react-native';

import { EMERGENCY_NUMBER } from '../config';
import { t } from '../i18n';
import { radius, spacing, useThemeColors } from '../theme';

/**
 * Persistent non-diagnostic disclaimer (TRD §3). Shown at the top of every
 * screen — this is a triage aid, not a diagnosis.
 */
export function Disclaimer() {
  const c = useThemeColors();

  return (
    <View style={[styles.container, { backgroundColor: c.chipInactiveBg, borderColor: c.border }]}>
      <Text style={[styles.title, { color: c.text }]}>{t('disclaimer.title')}</Text>
      <Text style={[styles.body, { color: c.textSecondary }]}>
        {t('disclaimer.body', { emergencyNumber: EMERGENCY_NUMBER })}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  title: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  body: {
    fontSize: 13,
    lineHeight: 19,
  },
});
