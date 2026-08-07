import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { EMERGENCY_NUMBER } from '../config';
import { SeverityBadge } from '../components/SeverityBadge';
import { t } from '../i18n';
import { radius, spacing, useThemeColors } from '../theme';
import { TriageResult } from '../types';

interface Props {
  result: TriageResult;
  onRestart: () => void;
  onOpenHistory: () => void;
}

export function ResultScreen({ result, onRestart, onOpenHistory }: Props) {
  const c = useThemeColors();

  function callEmergency() {
    Linking.openURL(`tel:${EMERGENCY_NUMBER}`).catch(() => {
      // RN has no global alert(); use Alert.alert so the fallback works on native.
      Alert.alert(t('result.alertTitle'), t('result.alertBody', { emergencyNumber: EMERGENCY_NUMBER }));
    });
  }

  return (
    <ScrollView style={styles.flex} contentContainerStyle={[styles.content, { backgroundColor: c.background }]}>
      <Text style={[styles.heading, { color: c.text }]}>{t('result.title')}</Text>

      <SeverityBadge result={result} />

      <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
        <Text style={[styles.cardTitle, { color: c.text }]}>{t('result.recommendedAction')}</Text>
        <Text style={[styles.cardBody, { color: c.textSecondary }]}>{result.recommendedAction}</Text>
      </View>

      <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
        <Text style={[styles.cardTitle, { color: c.text }]}>{t('result.triggeredTitle')}</Text>
        {result.triggeredReasons.length === 0 ? (
          <Text style={[styles.cardBody, { color: c.textSecondary }]}>{t('result.noReasons')}</Text>
        ) : (
          result.triggeredReasons.map((reason, index) => (
            <View
              key={index}
              style={[
                styles.reasonRow,
                { borderBottomColor: c.border },
                index === result.triggeredReasons.length - 1 && styles.lastRow,
              ]}>
              <View style={[styles.bullet, { backgroundColor: result.color }]} />
              <Text style={[styles.reasonText, { color: c.text }]}>{reason}</Text>
            </View>
          ))
        )}
      </View>

      {result.isEmergency && (
        <Pressable
          onPress={callEmergency}
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.emergencyButton,
            { backgroundColor: c.danger },
            pressed && { backgroundColor: c.dangerPressed },
          ]}>
          <Text style={styles.emergencyButtonText}>
            {t('result.callEmergency', { emergencyNumber: EMERGENCY_NUMBER })}
          </Text>
        </Pressable>
      )}

      <View style={styles.buttonRow}>
        <Pressable
          onPress={onRestart}
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.secondaryButton,
            { backgroundColor: c.chipInactiveBg, borderColor: c.border },
            pressed && { opacity: 0.7 },
          ]}>
          <Text style={[styles.secondaryText, { color: c.text }]}>{t('result.startOver')}</Text>
        </Pressable>
        <Pressable
          onPress={onOpenHistory}
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.secondaryButton,
            { backgroundColor: c.chipInactiveBg, borderColor: c.border },
            pressed && { opacity: 0.7 },
          ]}>
          <Text style={[styles.secondaryText, { color: c.accent }]}>{t('common.history')}</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl * 2,
    gap: spacing.lg,
  },
  heading: {
    fontSize: 28,
    fontWeight: '800',
  },
  card: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  cardBody: {
    fontSize: 15,
    lineHeight: 22,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  lastRow: {
    borderBottomWidth: 0,
  },
  bullet: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 7,
  },
  reasonText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  emergencyButton: {
    borderRadius: radius.lg,
    paddingVertical: 16,
    alignItems: 'center',
  },
  emergencyButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '800',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  secondaryButton: {
    flex: 1,
    borderRadius: radius.lg,
    borderWidth: 1,
    paddingVertical: 14,
    alignItems: 'center',
  },
  secondaryText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
