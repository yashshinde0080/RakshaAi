import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';

import { t } from '../i18n';
import { RED_FLAGS, SYMPTOMS, calculateTriage } from '../logic/triageEngine';
import { radius, spacing, useThemeColors } from '../theme';
import { RedFlags, TriageInput, TriageResult, Vitals } from '../types';

interface Props {
  onComplete: (input: TriageInput, result: TriageResult) => void;
  onOpenHistory: () => void;
}

const EMPTY_RED_FLAGS: RedFlags = {
  unresponsive: false,
  notBreathingOrGasping: false,
  strokeSigns: false,
  chestPainSevere: false,
  uncontrolledBleeding: false,
  anaphylaxisSigns: false,
  seizureActive: false,
};

const VITAL_FIELDS: Array<{
  key: keyof Vitals;
  label: string;
  unit: string;
  placeholder: string;
  keyboard: 'number-pad' | 'decimal-pad';
}> = [
  { key: 'heartRate', label: t('vital.heartRate'), unit: t('vital.heartRateUnit'), placeholder: t('vital.heartRatePlaceholder'), keyboard: 'number-pad' },
  { key: 'systolicBP', label: t('vital.systolicBP'), unit: t('vital.systolicBPUnit'), placeholder: t('vital.systolicBPPlaceholder'), keyboard: 'number-pad' },
  { key: 'spo2', label: t('vital.spo2'), unit: t('vital.spo2Unit'), placeholder: t('vital.spo2Placeholder'), keyboard: 'number-pad' },
  { key: 'temperatureC', label: t('vital.temperature'), unit: t('vital.temperatureUnit'), placeholder: t('vital.temperaturePlaceholder'), keyboard: 'decimal-pad' },
  { key: 'respiratoryRate', label: t('vital.respiratoryRate'), unit: t('vital.respiratoryRateUnit'), placeholder: t('vital.respiratoryRatePlaceholder'), keyboard: 'number-pad' },
];

export function TriageFormScreen({ onComplete, onOpenHistory }: Props) {
  const c = useThemeColors();
  const [redFlags, setRedFlags] = useState<RedFlags>(EMPTY_RED_FLAGS);
  const [vitals, setVitals] = useState<Record<keyof Vitals, string>>({
    heartRate: '',
    systolicBP: '',
    spo2: '',
    temperatureC: '',
    respiratoryRate: '',
  });
  const [painScore, setPainScore] = useState(0);
  const [durationHours, setDurationHours] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);

  function toggleRedFlag(key: keyof RedFlags) {
    setRedFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function toggleSymptom(id: string) {
    setSelectedSymptoms((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    );
  }

  function parseNumber(raw: string): number | undefined {
    // ponytail: Number('') is 0, which would trip critical-vitals checks for an
    // empty field. Blank input must mean "not provided", not 0 — the engine
    // tolerates undefined vitals per TRD §4.
    if (raw.trim() === '') {
      return undefined;
    }
    const value = Number(raw);
    return Number.isFinite(value) ? value : undefined;
  }

  function handleSubmit() {
    const input: TriageInput = {
      painScore,
      symptomDurationHours: parseNumber(durationHours),
      vitals: {
        heartRate: parseNumber(vitals.heartRate),
        systolicBP: parseNumber(vitals.systolicBP),
        spo2: parseNumber(vitals.spo2),
        temperatureC: parseNumber(vitals.temperatureC),
        respiratoryRate: parseNumber(vitals.respiratoryRate),
      },
      redFlags,
      otherSymptoms: selectedSymptoms,
    };
    onComplete(input, calculateTriage(input));
  }

  const sectionHeader = (title: string, hint?: string) => (
    <View style={styles.sectionHeader}>
      <Text style={[styles.sectionTitle, { color: c.text }]}>{title}</Text>
      {hint ? <Text style={[styles.sectionHint, { color: c.textSecondary }]}>{hint}</Text> : null}
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        style={styles.flex}
        contentContainerStyle={[styles.content, { backgroundColor: c.background }]}
        keyboardShouldPersistTaps="handled">
        <View style={styles.headerRow}>
          <Text style={[styles.heading, { color: c.text }]}>{t('common.appName')}</Text>
          <Pressable
            onPress={onOpenHistory}
            accessibilityRole="button"
            accessibilityLabel={t('form.viewHistoryA11y')}
            style={({ pressed }) => [
              styles.historyButton,
              { backgroundColor: c.chipInactiveBg, borderColor: c.border },
              pressed && { opacity: 0.7 },
            ]}>
            <Text style={[styles.historyButtonText, { color: c.accent }]}>{t('common.history')}</Text>
          </Pressable>
        </View>

        {sectionHeader(t('form.redFlagsTitle'), t('form.redFlagsHint'))}
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          {RED_FLAGS.map(({ key, label }, index) => (
            <View
              key={key}
              style={[
                styles.switchRow,
                { borderBottomColor: c.border },
                index === RED_FLAGS.length - 1 && styles.lastRow,
              ]}>
              <Text style={[styles.switchLabel, { color: c.text }]}>{label}</Text>
              <Switch
                value={redFlags[key]}
                onValueChange={() => toggleRedFlag(key)}
                trackColor={{ false: c.chipInactiveBg, true: c.danger }}
                thumbColor={redFlags[key] ? '#FFFFFF' : '#F1F5F9'}
              />
            </View>
          ))}
        </View>

        {sectionHeader(t('form.vitalsTitle'), t('form.vitalsHint'))}
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <View style={styles.vitalsGrid}>
            {VITAL_FIELDS.map((field) => (
              <View key={field.key} style={styles.vitalField}>
                <Text style={[styles.vitalLabel, { color: c.textSecondary }]}>{field.label}</Text>
                <View style={[styles.inputWrap, { backgroundColor: c.inputBg, borderColor: c.border }]}>
                  <TextInput
                    value={vitals[field.key]}
                    onChangeText={(text) =>
                      setVitals((prev) => ({ ...prev, [field.key]: text.replace(',', '.') }))
                    }
                    placeholder={field.placeholder}
                    placeholderTextColor={c.textSecondary}
                    keyboardType={field.keyboard}
                    style={[styles.input, { color: c.text }]}
                    accessibilityLabel={field.label}
                  />
                  <Text style={[styles.inputUnit, { color: c.textSecondary }]}>{field.unit}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>

        {sectionHeader(t('form.painTitle'), t('form.painHint'))}
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <View style={styles.painRow}>
            {Array.from({ length: 11 }, (_, i) => (
              <Pressable
                key={i}
                onPress={() => setPainScore(i)}
                accessibilityRole="button"
                accessibilityLabel={t('form.painA11y', { level: i })}
                accessibilityState={{ selected: painScore === i }}
                style={({ pressed }) => [
                  styles.painButton,
                  { backgroundColor: painScore === i ? c.accent : c.chipInactiveBg, borderColor: c.border },
                  pressed && { opacity: 0.7 },
                ]}>
                <Text
                  style={[
                    styles.painButtonText,
                    { color: painScore === i ? '#FFFFFF' : c.text },
                  ]}>
                  {i}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={[styles.painValue, { color: c.textSecondary }]}>
            {t('form.painSelected', { pain: painScore })}
          </Text>
        </View>

        {sectionHeader(t('form.durationTitle'), t('form.durationHint'))}
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <View style={[styles.inputWrap, { backgroundColor: c.inputBg, borderColor: c.border }]}>
            <TextInput
              value={durationHours}
              onChangeText={setDurationHours}
              placeholder={t('form.durationPlaceholder')}
              placeholderTextColor={c.textSecondary}
              keyboardType="number-pad"
              style={[styles.input, { color: c.text }]}
              accessibilityLabel={t('form.durationA11y')}
            />
            <Text style={[styles.inputUnit, { color: c.textSecondary }]}>{t('form.durationUnit')}</Text>
          </View>
        </View>

        {sectionHeader(t('form.symptomsTitle'), t('form.symptomsHint'))}
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
          <View style={styles.chipWrap}>
            {SYMPTOMS.map((symptom) => {
              const active = selectedSymptoms.includes(symptom.id);
              return (
                <Pressable
                  key={symptom.id}
                  onPress={() => toggleSymptom(symptom.id)}
                  accessibilityRole="button"
                  accessibilityLabel={symptom.label}
                  accessibilityState={{ selected: active }}
                  style={({ pressed }) => [
                    styles.chip,
                    {
                      backgroundColor: active ? c.chipActiveBg : c.chipInactiveBg,
                      borderColor: active ? c.chipActiveBg : c.border,
                    },
                    pressed && { opacity: 0.75 },
                  ]}>
                  <Text
                    style={[
                      styles.chipText,
                      { color: active ? c.chipActiveText : c.chipInactiveText },
                    ]}>
                    {symptom.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <Pressable
          onPress={handleSubmit}
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.submitButton,
            { backgroundColor: c.accent },
            pressed && { backgroundColor: c.accentPressed },
          ]}>
          <Text style={styles.submitText}>{t('form.submit')}</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
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
  historyButton: {
    borderRadius: radius.md,
    borderWidth: 1,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  historyButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  sectionHeader: {
    marginTop: spacing.sm,
    gap: 2,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  sectionHint: {
    fontSize: 12,
  },
  card: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.lg,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  lastRow: {
    borderBottomWidth: 0,
  },
  switchLabel: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  vitalsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  vitalField: {
    width: '47%',
    flexGrow: 1,
    gap: 6,
  },
  vitalLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    height: 48,
  },
  input: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 0,
  },
  inputUnit: {
    fontSize: 13,
  },
  painRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  painButton: {
    width: 44,
    height: 44,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  painButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  painValue: {
    marginTop: spacing.sm,
    fontSize: 13,
    textAlign: 'center',
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    borderRadius: radius.md,
    borderWidth: 1,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  chipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  submitButton: {
    marginTop: spacing.md,
    borderRadius: radius.lg,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
