import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { SeverityBadge } from '../components/SeverityBadge';
import { t } from '../i18n';
import { RED_FLAGS, getSymptomLabel } from '../logic/triageEngine';
import { radius, spacing, useThemeColors } from '../theme';
import { TriageRecord } from '../storage/record';

interface Props {
  records: TriageRecord[];
  onBack: () => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
}

const VITAL_LABELS: Record<string, string> = {
  heartRate: t('vital.heartRate'),
  systolicBP: t('vital.systolicBP'),
  spo2: t('vital.spo2'),
  temperatureC: t('vital.temperature'),
  respiratoryRate: t('vital.respiratoryRate'),
};

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleString();
}

export function HistoryScreen({ records, onBack, onDelete, onClearAll }: Props) {
  const c = useThemeColors();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = selectedId ? records.find((r) => r.id === selectedId) : undefined;

  function confirmClearAll() {
    Alert.alert(t('history.clearAllTitle'), t('history.clearAllBody'), [
      { text: t('history.cancel'), style: 'cancel' },
      { text: t('history.clearAll'), style: 'destructive', onPress: onClearAll },
    ]);
  }

  // ---- Detail view ----
  if (selected) {
    const redFlagLabels = RED_FLAGS.filter((rf) => selected.input.redFlags[rf.key]).map(
      (rf) => rf.label,
    );
    const separator = t('common.listSeparator');
    const vitals = Object.entries(selected.input.vitals)
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => `${VITAL_LABELS[key] ?? key}: ${value}`);
    const symptoms = selected.input.otherSymptoms.map(getSymptomLabel);

    return (
      <ScrollView style={styles.flex} contentContainerStyle={[styles.content, { backgroundColor: c.background }]}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => setSelectedId(null)} accessibilityRole="button" hitSlop={8}>
            <Text style={[styles.backLink, { color: c.accent }]}>{t('history.back')}</Text>
          </Pressable>
          <Pressable onPress={() => onDelete(selected.id)} accessibilityRole="button" hitSlop={8}>
            <Text style={[styles.dangerLink, { color: c.danger }]}>{t('history.delete')}</Text>
          </Pressable>
        </View>

        <Text style={[styles.meta, { color: c.textSecondary }]}>
          {formatTimestamp(selected.timestamp)}
        </Text>
        <SeverityBadge result={selected.result} />

        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <Text style={[styles.cardTitle, { color: c.text }]}>{t('result.recommendedAction')}</Text>
          <Text style={[styles.cardBody, { color: c.textSecondary }]}>
            {selected.result.recommendedAction}
          </Text>
        </View>

        {selected.result.triggeredReasons.length > 0 && (
          <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
            <Text style={[styles.cardTitle, { color: c.text }]}>{t('result.triggeredTitle')}</Text>
            {selected.result.triggeredReasons.map((reason, index) => (
              <Text key={index} style={[styles.reasonText, { color: c.text }]}>
                • {reason}
              </Text>
            ))}
          </View>
        )}

        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <Text style={[styles.cardTitle, { color: c.text }]}>{t('history.inputSummary')}</Text>
          {redFlagLabels.length > 0 && (
            <Text style={[styles.summaryLine, { color: c.text }]}>
              <Text style={styles.summaryLabel}>{t('history.redFlags')}</Text>
              {redFlagLabels.join(separator)}
            </Text>
          )}
          {vitals.length > 0 && (
            <Text style={[styles.summaryLine, { color: c.text }]}>
              <Text style={styles.summaryLabel}>{t('history.vitals')}</Text>
              {vitals.join(separator)}
            </Text>
          )}
          <Text style={[styles.summaryLine, { color: c.text }]}>              <Text style={styles.summaryLabel}>{t('history.pain')}</Text>
              {t('history.painValue', { pain: selected.input.painScore })}
          </Text>
          {selected.input.symptomDurationHours !== undefined && (
            <Text style={[styles.summaryLine, { color: c.text }]}>
              <Text style={styles.summaryLabel}>{t('history.duration')}</Text>
              {t('history.durationValue', { hours: selected.input.symptomDurationHours })}
            </Text>
          )}
          <Text style={[styles.summaryLine, { color: c.text }]}>              <Text style={styles.summaryLabel}>{t('history.symptoms')}</Text>
              {symptoms.length > 0 ? symptoms.join(separator) : t('history.noneReported')}
          </Text>
        </View>
      </ScrollView>
    );
  }

  // ---- List view ----
  return (
    <ScrollView style={styles.flex} contentContainerStyle={[styles.content, { backgroundColor: c.background }]}>
      <View style={styles.headerRow}>
        <Text style={[styles.heading, { color: c.text }]}>{t('history.title')}</Text>
        {records.length > 0 && (
          <Pressable onPress={confirmClearAll} accessibilityRole="button" hitSlop={8}>
            <Text style={[styles.dangerLink, { color: c.danger }]}>{t('history.clearAll')}</Text>
          </Pressable>
        )}
      </View>

      {records.length === 0 ? (
        <View style={[styles.emptyCard, { backgroundColor: c.surface, borderColor: c.border }]}>
          <Text style={[styles.emptyTitle, { color: c.text }]}>{t('history.emptyTitle')}</Text>
          <Text style={[styles.emptyBody, { color: c.textSecondary }]}>{t('history.emptyBody')}</Text>
          <Pressable
            onPress={onBack}
            accessibilityRole="button"
            style={({ pressed }) => [styles.primaryButton, { backgroundColor: c.accent }, pressed && { backgroundColor: c.accentPressed }]}>
            <Text style={styles.primaryButtonText}>{t('history.runAssessment')}</Text>
          </Pressable>
        </View>
      ) : (
        records.map((record) => (
          <Pressable
            key={record.id}
            onPress={() => setSelectedId(record.id)}
            accessibilityRole="button"
            accessibilityLabel={t('history.itemA11y', { date: formatTimestamp(record.timestamp) })}
            style={({ pressed }) => [
              styles.recordCard,
              { backgroundColor: c.surface, borderColor: c.border },
              pressed && { opacity: 0.75 },
            ]}>
            <View style={styles.recordHeader}>
              <Text style={[styles.recordDate, { color: c.textSecondary }]}>
                {formatTimestamp(record.timestamp)}
              </Text>
              <SeverityBadge result={record.result} variant="inline" />
            </View>
            {record.result.triggeredReasons[0] && (
              <Text style={[styles.recordReason, { color: c.textSecondary }]}>
                {record.result.triggeredReasons[0]}
              </Text>
            )}
          </Pressable>
        ))
      )}

      <Pressable
        onPress={onBack}
        accessibilityRole="button"
        style={({ pressed }) => [
          styles.secondaryButton,
          { backgroundColor: c.chipInactiveBg, borderColor: c.border },
          pressed && { opacity: 0.7 },
        ]}>
        <Text style={[styles.secondaryText, { color: c.text }]}>{t('history.backToAssessment')}</Text>
      </Pressable>
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
    gap: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  heading: {
    fontSize: 28,
    fontWeight: '800',
  },
  backLink: {
    fontSize: 17,
    fontWeight: '700',
  },
  dangerLink: {
    fontSize: 15,
    fontWeight: '700',
  },
  meta: {
    fontSize: 13,
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
  reasonText: {
    fontSize: 14,
    lineHeight: 20,
  },
  summaryLine: {
    fontSize: 14,
    lineHeight: 20,
  },
  summaryLabel: {
    fontWeight: '700',
  },
  emptyCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.xl,
    gap: spacing.md,
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: 17,
    fontWeight: '700',
  },
  emptyBody: {
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
  },
  primaryButton: {
    alignSelf: 'stretch',
    borderRadius: radius.lg,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  recordCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  recordHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  recordDate: {
    fontSize: 13,
    flexShrink: 1,
  },
  recordReason: {
    fontSize: 13,
    lineHeight: 18,
  },
  secondaryButton: {
    borderRadius: radius.lg,
    borderWidth: 1,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  secondaryText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
