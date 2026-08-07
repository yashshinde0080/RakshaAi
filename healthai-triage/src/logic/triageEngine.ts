/**
 * Triage Engine — the safety-critical core (TRD §5).
 *
 * `calculateTriage` is a PURE function evaluated in strict priority order.
 * Each step short-circuits: once a level is determined, no lower-priority
 * checks run. Ties always resolve to the more severe level.
 *
 * Every returned `triggeredReasons` entry maps to a concrete condition
 * checked in this file — no free-text or inferred explanations.
 */

import { RedFlags, SeverityLevel, TriageInput, TriageResult, Vitals } from '../types';
import { t } from '../i18n';

export type SymptomTag = 'highRisk' | 'giDehydration' | 'fracture';

export interface Symptom {
  id: string;
  label: string;
  tag?: SymptomTag;
}

/** Curated symptom catalog shared by the form (checkbox labels) and engine (tags). */
export const SYMPTOMS: Symptom[] = [
  // High-risk tags → emergent (Level 2)
  { id: 'chestPain', label: t('symptom.chestPain'), tag: 'highRisk' },
  { id: 'shortnessOfBreath', label: t('symptom.shortnessOfBreath'), tag: 'highRisk' },
  { id: 'worstHeadache', label: t('symptom.worstHeadache'), tag: 'highRisk' },
  { id: 'confusion', label: t('symptom.confusion'), tag: 'highRisk' },
  { id: 'fainting', label: t('symptom.fainting'), tag: 'highRisk' },
  { id: 'coughingBlood', label: t('symptom.coughingBlood'), tag: 'highRisk' },
  { id: 'severeAbdominalPain', label: t('symptom.severeAbdominalPain'), tag: 'highRisk' },
  { id: 'oneSidedWeakness', label: t('symptom.oneSidedWeakness'), tag: 'highRisk' },
  // GI/dehydration tags → urgent (Level 3)
  { id: 'vomiting', label: t('symptom.vomiting'), tag: 'giDehydration' },
  { id: 'diarrhea', label: t('symptom.diarrhea'), tag: 'giDehydration' },
  { id: 'dehydrationSigns', label: t('symptom.dehydrationSigns'), tag: 'giDehydration' },
  { id: 'unableToKeepFluids', label: t('symptom.unableToKeepFluids'), tag: 'giDehydration' },
  // Fracture tag → urgent (Level 3)
  { id: 'suspectedFracture', label: t('symptom.suspectedFracture'), tag: 'fracture' },
  // Other symptoms → less urgent (Level 4)
  { id: 'fever', label: t('symptom.fever') },
  { id: 'cough', label: t('symptom.cough') },
  { id: 'soreThroat', label: t('symptom.soreThroat') },
  { id: 'fatigue', label: t('symptom.fatigue') },
  { id: 'mildHeadache', label: t('symptom.mildHeadache') },
  { id: 'nausea', label: t('symptom.nausea') },
  { id: 'rash', label: t('symptom.rash') },
  { id: 'jointPain', label: t('symptom.jointPain') },
];

const symptomById = new Map(SYMPTOMS.map((s) => [s.id, s]));

export function getSymptomLabel(id: string): string {
  return symptomById.get(id)?.label ?? id;
}

const RED_FLAG_LABELS: Array<[keyof RedFlags, string]> = [
  ['unresponsive', t('redFlag.unresponsive')],
  ['notBreathingOrGasping', t('redFlag.notBreathing')],
  ['strokeSigns', t('redFlag.strokeSigns')],
  ['chestPainSevere', t('redFlag.chestPain')],
  ['uncontrolledBleeding', t('redFlag.uncontrolledBleeding')],
  ['anaphylaxisSigns', t('redFlag.anaphylaxis')],
  ['seizureActive', t('redFlag.seizure')],
];

/** Red flag keys + labels, exported for the intake form. */
export const RED_FLAGS: ReadonlyArray<{ key: keyof RedFlags; label: string }> = RED_FLAG_LABELS.map(
  ([key, label]) => ({ key, label }),
);

const SEVERITY_META: Record<
  SeverityLevel,
  { label: string; color: string; recommendedAction: string; isEmergency: boolean }
> = {
  [SeverityLevel.LEVEL_1]: {
    label: t('severity.level1Label'),
    color: '#DC2626',
    recommendedAction: t('severity.level1Action'),
    isEmergency: true,
  },
  [SeverityLevel.LEVEL_2]: {
    label: t('severity.level2Label'),
    color: '#EA580C',
    recommendedAction: t('severity.level2Action'),
    isEmergency: true,
  },
  [SeverityLevel.LEVEL_3]: {
    label: t('severity.level3Label'),
    color: '#D97706',
    recommendedAction: t('severity.level3Action'),
    isEmergency: false,
  },
  [SeverityLevel.LEVEL_4]: {
    label: t('severity.level4Label'),
    color: '#2563EB',
    recommendedAction: t('severity.level4Action'),
    isEmergency: false,
  },
  [SeverityLevel.LEVEL_5]: {
    label: t('severity.level5Label'),
    color: '#16A34A',
    recommendedAction: t('severity.level5Action'),
    isEmergency: false,
  },
};

function buildResult(level: SeverityLevel, triggeredReasons: string[]): TriageResult {
  const meta = SEVERITY_META[level];
  return {
    level,
    label: meta.label,
    color: meta.color,
    recommendedAction: meta.recommendedAction,
    triggeredReasons,
    isEmergency: meta.isEmergency,
  };
}

/** Step 1: any red flag → Level 1, unconditionally. */
function redFlagReasons(redFlags: RedFlags): string[] {
  return RED_FLAG_LABELS.filter(([key]) => redFlags[key]).map(([, label]) =>
    t('reason.redFlag', { label }),
  );
}

/** Step 2: critical vitals → Level 1. */
function criticalVitalReasons(v: Vitals): string[] {
  // ponytail: thresholds follow TRD §5 exactly, so HR=40 and RR=8 fall between
  // the critical (<40/<8) and borderline (41-49/9-10) bands and are not caught.
  // Clinically those are slow but the spec draws the line at <40/<8; add a
  // check here only if clinical sign-off narrows the boundary.
  const reasons: string[] = [];
  if (v.spo2 !== undefined && v.spo2 < 90) {
    reasons.push(t('reason.spo2Critical', { value: v.spo2 }));
  }
  if (v.systolicBP !== undefined && (v.systolicBP < 90 || v.systolicBP > 200)) {
    reasons.push(t('reason.bpCritical', { value: v.systolicBP }));
  }
  if (v.heartRate !== undefined && (v.heartRate < 40 || v.heartRate > 150)) {
    reasons.push(t('reason.hrCritical', { value: v.heartRate }));
  }
  if (v.respiratoryRate !== undefined && (v.respiratoryRate < 8 || v.respiratoryRate > 30)) {
    reasons.push(t('reason.rrCritical', { value: v.respiratoryRate }));
  }
  return reasons;
}

/** Step 3: emergent signals → Level 2. */
function emergentReasons(input: TriageInput): string[] {
  const reasons: string[] = [];
  const v = input.vitals;

  if (v.spo2 !== undefined && v.spo2 >= 90 && v.spo2 <= 94) {
    reasons.push(t('reason.spo2Borderline', { value: v.spo2 }));
  }
  if (v.systolicBP !== undefined && ((v.systolicBP >= 90 && v.systolicBP <= 99) || (v.systolicBP >= 181 && v.systolicBP <= 200))) {
    reasons.push(t('reason.bpBorderline', { value: v.systolicBP }));
  }
  if (v.heartRate !== undefined && ((v.heartRate >= 41 && v.heartRate <= 49) || (v.heartRate >= 121 && v.heartRate <= 150))) {
    reasons.push(t('reason.hrBorderline', { value: v.heartRate }));
  }
  if (v.respiratoryRate !== undefined && ((v.respiratoryRate >= 9 && v.respiratoryRate <= 10) || (v.respiratoryRate >= 26 && v.respiratoryRate <= 30))) {
    reasons.push(t('reason.rrBorderline', { value: v.respiratoryRate }));
  }
  if (v.temperatureC !== undefined && v.temperatureC >= 39.5) {
    reasons.push(t('reason.highFever', { value: v.temperatureC }));
  }
  if (v.temperatureC !== undefined && v.temperatureC <= 35.0) {
    reasons.push(t('reason.hypothermia', { value: v.temperatureC }));
  }

  for (const id of input.otherSymptoms) {
    if (symptomById.get(id)?.tag === 'highRisk') {
      reasons.push(t('reason.highRiskSymptom', { label: getSymptomLabel(id) }));
    }
  }

  if (input.painScore >= 9) {
    reasons.push(t('reason.painSevere', { value: input.painScore }));
  }
  return reasons;
}

/** Step 4: urgent signals → Level 3. */
function urgentReasons(input: TriageInput): string[] {
  const reasons: string[] = [];

  for (const id of input.otherSymptoms) {
    const tag = symptomById.get(id)?.tag;
    if (tag === 'giDehydration') {
      reasons.push(t('reason.giDehydration', { label: getSymptomLabel(id) }));
    } else if (tag === 'fracture') {
      reasons.push(t('reason.fracture', { label: getSymptomLabel(id) }));
    }
  }

  if (input.painScore >= 6) {
    reasons.push(t('reason.painSignificant', { value: input.painScore }));
  }

  if (input.symptomDurationHours !== undefined && input.symptomDurationHours >= 48) {
    reasons.push(t('reason.durationLong', { value: input.symptomDurationHours }));
  }
  return reasons;
}

/** Step 5: less urgent → Level 4. */
function lessUrgentReasons(input: TriageInput): string[] {
  const reasons: string[] = [];

  if (input.painScore >= 3) {
    reasons.push(t('reason.painMild', { value: input.painScore }));
  }

  for (const id of input.otherSymptoms) {
    if (symptomById.get(id)?.tag === undefined) {
      reasons.push(t('reason.symptom', { label: getSymptomLabel(id) }));
    }
  }
  return reasons;
}

/**
 * Pure triage assessment (TRD §5). Runs in constant time (< 1ms),
 * no I/O, no side effects — safe to call synchronously from the UI.
 */
export function calculateTriage(input: TriageInput): TriageResult {
  const redFlags = redFlagReasons(input.redFlags);
  if (redFlags.length > 0) {
    return buildResult(SeverityLevel.LEVEL_1, redFlags);
  }

  const critical = criticalVitalReasons(input.vitals);
  if (critical.length > 0) {
    return buildResult(SeverityLevel.LEVEL_1, critical);
  }

  const emergent = emergentReasons(input);
  if (emergent.length > 0) {
    return buildResult(SeverityLevel.LEVEL_2, emergent);
  }

  const urgent = urgentReasons(input);
  if (urgent.length > 0) {
    return buildResult(SeverityLevel.LEVEL_3, urgent);
  }

  const lessUrgent = lessUrgentReasons(input);
  if (lessUrgent.length > 0) {
    return buildResult(SeverityLevel.LEVEL_4, lessUrgent);
  }

  return buildResult(SeverityLevel.LEVEL_5, []);
}
