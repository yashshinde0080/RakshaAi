import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
} from 'react-native';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { errMsg, runTriage } from '@/api';
import { clearTriage, deleteTriage, listTriage, saveTriage } from '@/storage/triageDb';
import type { TriageHistoryRow } from '@/storage/triageDb';
import type { TriageInput, TriageResult } from '@/types';

// Region-configurable emergency number (PRD: config, not hardcoded).
const EMERGENCY_NUMBER = '112';

const SEVERITY_COLORS: Record<number, string> = {
  1: '#D32F2F',
  2: '#F57C00',
  3: '#F9A825',
  4: '#7CB342',
  5: '#388E3C',
};

const RED_FLAG_LIST: { key: keyof TriageInput['red_flags']; label: string }[] = [
  { key: 'unresponsive', label: 'Unresponsive / unconscious' },
  { key: 'not_breathing', label: 'Not breathing or gasping' },
  { key: 'stroke_signs', label: 'Stroke signs (face, arm, speech)' },
  { key: 'chest_pain_severe', label: 'Severe chest pain or pressure' },
  { key: 'uncontrolled_bleeding', label: 'Uncontrolled bleeding' },
  { key: 'anaphylaxis_signs', label: 'Anaphylaxis signs (swelling, hives)' },
  { key: 'seizure_active', label: 'Active seizure' },
];

const SYMPTOM_GROUPS: { title: string; items: { id: string; label: string }[] }[] = [
  {
    title: 'High risk',
    items: [
      { id: 'chest_pain', label: 'Chest pain / tightness' },
      { id: 'shortness_of_breath', label: 'Shortness of breath' },
      { id: 'sudden_severe_headache', label: 'Sudden severe headache' },
      { id: 'confusion', label: 'Confusion' },
      { id: 'fainting', label: 'Fainting' },
      { id: 'coughing_blood', label: 'Coughing blood' },
      { id: 'severe_abdominal_pain', label: 'Severe abdominal pain' },
      { id: 'one_sided_weakness', label: 'One-sided weakness' },
    ],
  },
  {
    title: 'GI / dehydration',
    items: [
      { id: 'vomiting', label: 'Vomiting' },
      { id: 'diarrhea', label: 'Diarrhea' },
      { id: 'dehydration_signs', label: 'Signs of dehydration' },
      { id: 'unable_to_keep_fluids', label: 'Cannot keep fluids down' },
    ],
  },
  {
    title: 'Other',
    items: [
      { id: 'suspected_fracture', label: 'Suspected fracture' },
      { id: 'fever', label: 'Fever' },
      { id: 'cough', label: 'Cough' },
      { id: 'sore_throat', label: 'Sore throat' },
      { id: 'rash', label: 'Rash' },
      { id: 'headache', label: 'Headache' },
      { id: 'dizziness', label: 'Dizziness' },
      { id: 'nausea', label: 'Nausea' },
      { id: 'fatigue', label: 'Fatigue' },
      { id: 'back_pain', label: 'Back pain' },
      { id: 'joint_pain', label: 'Joint pain' },
    ],
  },
];

const GENDER_OPTIONS: { value: TriageInput['vitals']['gender']; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

interface FormState {
  age: string;
  pain: number;
  duration: string;
  hr: string;
  sbp: string;
  spo2: string;
  temp: string;
  rr: string;
  gender: TriageInput['vitals']['gender'] | '';
  flags: TriageInput['red_flags'];
  symptoms: string[];
}

const EMPTY_FORM: FormState = {
  age: '',
  pain: 0,
  duration: '',
  hr: '',
  sbp: '',
  spo2: '',
  temp: '',
  rr: '',
  gender: '',
  flags: {
    unresponsive: false,
    not_breathing: false,
    stroke_signs: false,
    chest_pain_severe: false,
    uncontrolled_bleeding: false,
    anaphylaxis_signs: false,
    seizure_active: false,
  },
  symptoms: [],
};

// Front gate, mirrored from the backend validator: impossible vitals never
// leave the device.
function validateForm(f: FormState): string[] {
  const errors: string[] = [];
  const num = (s: string): number | undefined =>
    s.trim() === '' ? undefined : Number(s);
  const bound = (label: string, v: number | undefined, lo: number, hi: number) => {
    if (v !== undefined && (Number.isNaN(v) || v < lo || v > hi)) {
      errors.push(`${label} must be ${lo}-${hi}`);
    }
  };
  bound('Heart rate', num(f.hr), 20, 250);
  bound('Systolic BP', num(f.sbp), 40, 300);
  bound('SpO2', num(f.spo2), 50, 100);
  bound('Temperature', num(f.temp), 30, 45);
  bound('Respiratory rate', num(f.rr), 4, 80);
  const age = num(f.age);
  if (age !== undefined && (Number.isNaN(age) || age < 0 || age > 120)) {
    errors.push('Age must be 0-120');
  }
  const dur = num(f.duration);
  if (dur !== undefined && dur < 0) errors.push('Duration cannot be negative');
  return errors;
}

function toInput(f: FormState): TriageInput {
  const num = (s: string): number | undefined =>
    s.trim() === '' ? undefined : Number(s);
  return {
    age_years: num(f.age) ?? 0,
    pain_score: f.pain,
    symptom_duration_hours: num(f.duration) ?? 0,
    vitals: {
      heart_rate: num(f.hr),
      systolic_bp: num(f.sbp),
      spo2: num(f.spo2),
      temperature_c: num(f.temp),
      respiratory_rate: num(f.rr),
      gender: f.gender === '' ? undefined : f.gender,
    },
    red_flags: f.flags,
    symptoms: f.symptoms,
  };
}

export default function TriageScreen() {
  const theme = useTheme();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [result, setResult] = useState<TriageResult | null>(null);
  const [history, setHistory] = useState<TriageHistoryRow[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reloadHistory = useCallback(() => setHistory(listTriage()), []);

  useEffect(() => {
    reloadHistory();
  }, [reloadHistory]);

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));
  const toggleFlag = (key: keyof TriageInput['red_flags']) =>
    setForm((f) => ({ ...f, flags: { ...f.flags, [key]: !f.flags[key] } }));
  const toggleSymptom = (id: string) =>
    setForm((f) => ({
      ...f,
      symptoms: f.symptoms.includes(id)
        ? f.symptoms.filter((s) => s !== id)
        : [...f.symptoms, id],
    }));

  const submit = async () => {
    const errors = validateForm(form);
    if (errors.length > 0) {
      setError(errors.join(' · '));
      return;
    }
    setError(null);
    setRunning(true);
    try {
      const input = toInput(form);
      const res = await runTriage(input);
      setResult(res);
      saveTriage(input, res);
      reloadHistory();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setRunning(false);
    }
  };

  const callEmergency = () => {
    Linking.openURL(`tel:${EMERGENCY_NUMBER}`).catch(() =>
      Alert.alert('Call not available', `Please dial ${EMERGENCY_NUMBER} on your phone.`)
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.list}>
      <Disclaimer />
      {error && <ErrorBanner message={error} />}

      <Section title="Red flags">
        <ThemedText type="small" themeColor="textSecondary" style={styles.hint}>
          Any of these means the result jumps to level 1.
        </ThemedText>
        {RED_FLAG_LIST.map((flag) => (
          <ToggleRow
            key={flag.key}
            label={flag.label}
            value={form.flags[flag.key]}
            onPress={() => toggleFlag(flag.key)}
          />
        ))}
      </Section>

      <Section title="Vitals">
        <VitalsGrid form={form} set={set} />
        <ThemedText type="small" themeColor="textSecondary" style={styles.genderLabel}>
          Gender
        </ThemedText>
        <ThemedView style={styles.chips}>
          {GENDER_OPTIONS.map((g) => (
            <Pressable
              key={g.value}
              onPress={() => set({ gender: form.gender === g.value ? '' : g.value })}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedView type={form.gender === g.value ? 'backgroundSelected' : 'background'} style={styles.chip}>
                <ThemedText type="small">{g.label}</ThemedText>
              </ThemedView>
            </Pressable>
          ))}
        </ThemedView>
      </Section>

      <Section title="Pain & duration">
        <ThemedView style={styles.row}>
          <ThemedText type="small" style={styles.rowLabel}>
            Pain (0-10)
          </ThemedText>
          <ThemedView style={styles.stepper}>
            <Pressable
              onPress={() => set({ pain: Math.max(0, form.pain - 1) })}
              hitSlop={8}
              style={({ pressed }) => [styles.stepButton, { backgroundColor: theme.background }, pressed && styles.pressed]}>
              <ThemedText type="smallBold">−</ThemedText>
            </Pressable>
            <ThemedText type="smallBold" style={styles.stepValue}>
              {form.pain}
            </ThemedText>
            <Pressable
              onPress={() => set({ pain: Math.min(10, form.pain + 1) })}
              hitSlop={8}
              style={({ pressed }) => [styles.stepButton, { backgroundColor: theme.background }, pressed && styles.pressed]}>
              <ThemedText type="smallBold">+</ThemedText>
            </Pressable>
          </ThemedView>
        </ThemedView>
        <FieldRow label="Age (years)" value={form.age} onChangeText={(v) => set({ age: v })} keyboardType="numeric" />
        <FieldRow
          label="Symptom duration (hours)"
          value={form.duration}
          onChangeText={(v) => set({ duration: v })}
          keyboardType="numeric"
        />
      </Section>

      <Section title="Symptoms">
        {SYMPTOM_GROUPS.map((group) => (
          <ThemedView key={group.title} style={styles.symptomGroup}>
            <ThemedText type="small" themeColor="textSecondary">
              {group.title}
            </ThemedText>
            <ThemedView style={styles.chips}>
              {group.items.map((s) => (
                <Pressable
                  key={s.id}
                  onPress={() => toggleSymptom(s.id)}
                  style={({ pressed }) => pressed && styles.pressed}>
                  <ThemedView type={form.symptoms.includes(s.id) ? 'backgroundSelected' : 'background'} style={styles.chip}>
                    <ThemedText type="small">{s.label}</ThemedText>
                  </ThemedView>
                </Pressable>
              ))}
            </ThemedView>
          </ThemedView>
        ))}
      </Section>

      <Pressable
        onPress={submit}
        disabled={running}
        style={({ pressed }) => [
          styles.runButton,
          { backgroundColor: theme.backgroundSelected },
          (pressed || running) && styles.pressed,
        ]}>
        {running ? (
          <ActivityIndicator size="small" />
        ) : (
          <ThemedText type="smallBold">Run Triage</ThemedText>
        )}
      </Pressable>

      {result && <ResultCard result={result} onCall={callEmergency} />}

      <Section title="History">
        {history.length === 0 ? (
          <ThemedText type="small" themeColor="textSecondary">
            No past assessments. Results are stored only on this device.
          </ThemedText>
        ) : (
          <>
            {history.map((row) => (
              <Pressable
                key={row.id}
                onPress={() => setResult(row.result)}
                style={({ pressed }) => pressed && styles.pressed}>
                <ThemedView type="background" style={styles.historyRow}>
                  <ThemedView style={styles.historyInfo}>
                    <ThemedText type="smallBold">
                      Level {row.result.severity} · {row.result.label}
                    </ThemedText>
                    <ThemedText type="small" themeColor="textSecondary">
                      {new Date(row.created_at).toLocaleString()} · via {row.result.source}
                    </ThemedText>
                  </ThemedView>
                  <Pressable
                    onPress={() => {
                      deleteTriage(row.id);
                      reloadHistory();
                    }}
                    hitSlop={8}>
                    <ThemedText type="small" style={{ color: theme.error }}>
                      Delete
                    </ThemedText>
                  </Pressable>
                </ThemedView>
              </Pressable>
            ))}
            <Pressable
              onPress={() => {
                clearTriage();
                reloadHistory();
              }}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" themeColor="textSecondary" style={styles.clearAll}>
                Clear all history
              </ThemedText>
            </Pressable>
          </>
        )}
      </Section>
    </ScrollView>
  );
}

// ── Building blocks ─────────────────────────────────────────────────────────

function Disclaimer() {
  return (
    <ThemedView type="backgroundElement" style={styles.disclaimer}>
      <ThemedText type="small" themeColor="textSecondary">
        Not a medical diagnosis. Decision-support aid only — in an emergency call {EMERGENCY_NUMBER} immediately.
      </ThemedText>
    </ThemedView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        {title}
      </ThemedText>
      {children}
    </ThemedView>
  );
}

function ToggleRow({ label, value, onPress }: { label: string; value: boolean; onPress: () => void }) {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <ThemedView
        type={value ? 'backgroundSelected' : 'background'}
        style={[styles.toggleRow, value && { borderColor: theme.error, borderWidth: 1 }]}>
        <ThemedText type="small" style={styles.rowLabel}>
          {value ? '⚠ ' : ''}
          {label}
        </ThemedText>
        <ThemedText type="smallBold" themeColor={value ? 'error' : 'textSecondary'}>
          {value ? 'Yes' : 'No'}
        </ThemedText>
      </ThemedView>
    </Pressable>
  );
}

function FieldRow({
  label,
  value,
  onChangeText,
  keyboardType,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  keyboardType?: 'numeric';
}) {
  const theme = useTheme();
  return (
    <ThemedView style={styles.row}>
      <ThemedText type="small" style={styles.rowLabel}>
        {label}
      </ThemedText>
      <TextInput
        style={[styles.input, { color: theme.text, backgroundColor: theme.background }]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholder="—"
        placeholderTextColor={theme.textSecondary}
      />
    </ThemedView>
  );
}

function VitalsGrid({ form, set }: { form: FormState; set: (p: Partial<FormState>) => void }) {
  const items: {
    key: 'hr' | 'sbp' | 'spo2' | 'temp' | 'rr';
    label: string;
    placeholder: string;
  }[] = [
    { key: 'hr', label: 'Heart rate (bpm)', placeholder: '72' },
    { key: 'sbp', label: 'Systolic BP (mmHg)', placeholder: '120' },
    { key: 'spo2', label: 'SpO2 (%)', placeholder: '98' },
    { key: 'temp', label: 'Temp (°C)', placeholder: '37.0' },
    { key: 'rr', label: 'Respiratory rate', placeholder: '16' },
  ];
  return (
    <ThemedView style={styles.vitalsGrid}>
      {items.map((item) => (
        <FieldRow
          key={item.key}
          label={item.label}
          value={form[item.key]}
          onChangeText={(v) => set({ [item.key]: v })}
          keyboardType="numeric"
        />
      ))}
    </ThemedView>
  );
}

function ResultCard({ result, onCall }: { result: TriageResult; onCall: () => void }) {
  const theme = useTheme();
  const color = SEVERITY_COLORS[result.severity] ?? SEVERITY_COLORS[5];
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        Triage result
      </ThemedText>
      <ThemedView style={[styles.badge, { backgroundColor: color }]}>
        <ThemedText type="smallBold" style={styles.badgeText}>
          ESI Level {result.severity}
        </ThemedText>
      </ThemedView>
      <ThemedText type="smallBold">{result.label}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {result.recommended_action}
      </ThemedText>
      <ThemedView style={styles.sourceRow}>
        <ThemedText type="small" themeColor="textSecondary">
          via {result.source === 'rules' ? 'rule engine' : `AI model${result.source === 'llm_retry' ? ' (retry)' : ''}`}
        </ThemedText>
        {result.escalated && (
          <ThemedText type="small" style={{ color: theme.error }}>
            raised to rule level for safety
          </ThemedText>
        )}
      </ThemedView>
      {result.red_flags.length > 0 && (
        <ThemedView style={styles.reasonList}>
          <ThemedText type="smallBold">Red flags</ThemedText>
          {result.red_flags.map((r, i) => (
            <ThemedText key={i} type="small" themeColor="textSecondary">
              • {r}
            </ThemedText>
          ))}
        </ThemedView>
      )}
      {result.reasons.length > 0 && (
        <ThemedView style={styles.reasonList}>
          <ThemedText type="smallBold">Why</ThemedText>
          {result.reasons.map((r, i) => (
            <ThemedText key={i} type="small" themeColor="textSecondary">
              • {r}
            </ThemedText>
          ))}
        </ThemedView>
      )}
      {result.is_emergency && (
        <Pressable
          onPress={onCall}
          style={({ pressed }) => [
            styles.emergencyButton,
            { backgroundColor: SEVERITY_COLORS[1] },
            pressed && styles.pressed,
          ]}>
          <ThemedText type="smallBold" style={styles.badgeText}>
            Call {EMERGENCY_NUMBER} now
          </ThemedText>
        </Pressable>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  list: {
    padding: Spacing.three,
    gap: Spacing.three,
    paddingBottom: Spacing.six,
  },
  disclaimer: {
    borderRadius: Spacing.two,
    padding: Spacing.two,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  hint: {
    marginBottom: Spacing.one,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  rowLabel: {
    flex: 1,
  },
  input: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 15,
    minWidth: 90,
    textAlign: 'right',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    gap: Spacing.two,
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  stepButton: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  stepValue: {
    minWidth: 32,
    textAlign: 'center',
  },
  vitalsGrid: {
    gap: Spacing.two,
  },
  genderLabel: {
    marginTop: Spacing.two,
  },
  symptomGroup: {
    gap: Spacing.one,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  chip: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  runButton: {
    borderRadius: Spacing.three,
    paddingVertical: Spacing.three,
    alignItems: 'center',
    minHeight: 46,
    justifyContent: 'center',
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  badgeText: {
    color: '#ffffff',
  },
  sourceRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    alignItems: 'center',
  },
  reasonList: {
    gap: Spacing.half,
  },
  emergencyButton: {
    borderRadius: Spacing.three,
    paddingVertical: Spacing.three,
    alignItems: 'center',
  },
  historyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
    borderRadius: Spacing.two,
    padding: Spacing.two,
  },
  historyInfo: {
    flex: 1,
    gap: Spacing.half,
  },
  clearAll: {
    textAlign: 'center',
    paddingVertical: Spacing.two,
  },
  pressed: {
    opacity: 0.5,
  },
});
