/**
 * Data model for the HealthAI Triage engine (TRD §4).
 * All fields except red flags and pain score are optional-tolerant:
 * missing values simply skip their check rather than erroring.
 */

export enum SeverityLevel {
  LEVEL_1 = 1,
  LEVEL_2,
  LEVEL_3,
  LEVEL_4,
  LEVEL_5,
}

export interface Vitals {
  heartRate?: number; // bpm
  systolicBP?: number; // mmHg
  spo2?: number; // %
  temperatureC?: number; // °C
  respiratoryRate?: number; // breaths/min
}

export interface RedFlags {
  unresponsive: boolean;
  notBreathingOrGasping: boolean;
  strokeSigns: boolean;
  chestPainSevere: boolean;
  uncontrolledBleeding: boolean;
  anaphylaxisSigns: boolean;
  seizureActive: boolean;
}

export interface TriageInput {
  // ponytail: ageYears is defined per TRD §4 but the MVP rules in TRD §5 never
  // branch on age. Not collected in the form until pediatric/elderly
  // thresholds exist. Add age-specific rules before surfacing this field.
  ageYears?: number;
  painScore: number; // 0-10
  symptomDurationHours?: number;
  vitals: Vitals;
  redFlags: RedFlags;
  otherSymptoms: string[];
}

export interface TriageResult {
  level: SeverityLevel;
  label: string;
  color: string;
  recommendedAction: string;
  triggeredReasons: string[];
  isEmergency: boolean; // true for Level 1 & 2
}
