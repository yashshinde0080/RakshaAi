/**
 * English string catalog — the single source of truth for every user-facing
 * string (PRD §8: localization-ready).
 *
 * - Keys are dotted paths into a nested object (`t('reason.spo2Critical')`).
 *   A translation module (e.g. `fr.ts`) is typed as `StringCatalog` and must
 *   mirror the same nesting — a missing or extra key fails typecheck.
 * - Interpolation uses `{param}` placeholders, rendered by `t()` in index.ts.
 * - Rendered output must stay byte-identical to the original literals — the
 *   engine tests assert exact reason strings.
 *
 * Brand identity (APP_NAME) lives here under `common.appName`; region config
 * (EMERGENCY_NUMBER) stays in `config.ts` — it is a setting, not copy.
 */

export const en = {
  common: {
    appName: 'HealthAI Triage',
    history: 'History',
    // Locale-dependent list separator (CJK uses '、' etc.) — used for joined
    // symptom/vital lists in the history detail view.
    listSeparator: ', ',
  },

  severity: {
    levelName: 'Level {level}',
    level1Label: 'Immediate emergency',
    level1Action:
      'Call emergency services now and follow their instructions, or go to the nearest emergency department immediately.',
    level2Label: 'Emergency',
    level2Action:
      'Seek emergency care now. Call emergency services if you cannot reach care quickly or if symptoms worsen.',
    level3Label: 'Urgent',
    level3Action:
      'Seek medical attention within a few hours. Contact your doctor, clinic, or urgent care today.',
    level4Label: 'Less urgent',
    level4Action:
      'Seek non-urgent care. Contact your doctor or clinic within the next day or two if symptoms persist.',
    level5Label: 'Non-urgent',
    level5Action: 'Home care is likely sufficient. Monitor symptoms and seek care if they worsen.',
  },

  disclaimer: {
    title: 'Not a medical diagnosis',
    body:
      'This tool offers guidance only and does not replace professional medical care. If this is a life-threatening emergency, call {emergencyNumber} immediately.',
  },

  redFlag: {
    unresponsive: 'Unresponsive or difficult to wake',
    notBreathing: 'Not breathing, or only gasping',
    strokeSigns: 'Signs of stroke (face drooping, arm weakness, speech difficulty)',
    chestPain: 'Severe chest pain or pressure',
    uncontrolledBleeding: 'Uncontrolled bleeding',
    anaphylaxis: 'Signs of anaphylaxis (swollen face/lips, trouble breathing, hives)',
    seizure: 'Active seizure',
  },

  symptom: {
    chestPain: 'Chest pain or tightness',
    shortnessOfBreath: 'Shortness of breath',
    worstHeadache: 'Sudden, severe headache',
    confusion: 'Confusion or disorientation',
    fainting: 'Fainting or feeling about to faint',
    coughingBlood: 'Coughing up blood',
    severeAbdominalPain: 'Severe abdominal pain',
    oneSidedWeakness: 'Weakness or numbness on one side',
    vomiting: 'Vomiting',
    diarrhea: 'Diarrhea',
    dehydrationSigns: 'Signs of dehydration (dry mouth, dark urine, dizziness)',
    unableToKeepFluids: 'Unable to keep fluids down',
    suspectedFracture: 'Suspected fracture (pain, swelling, deformity after injury)',
    fever: 'Fever',
    cough: 'Cough',
    soreThroat: 'Sore throat',
    fatigue: 'Fatigue',
    mildHeadache: 'Mild headache',
    nausea: 'Nausea',
    rash: 'Rash',
    jointPain: 'Joint pain',
  },

  vital: {
    heartRate: 'Heart rate',
    heartRateUnit: 'bpm',
    heartRatePlaceholder: 'e.g. 72',
    systolicBP: 'Systolic BP',
    systolicBPUnit: 'mmHg',
    systolicBPPlaceholder: 'e.g. 120',
    spo2: 'SpO2',
    spo2Unit: '%',
    spo2Placeholder: 'e.g. 98',
    temperature: 'Temperature',
    temperatureUnit: '°C',
    temperaturePlaceholder: 'e.g. 37.0',
    respiratoryRate: 'Resp. rate',
    respiratoryRateUnit: '/min',
    respiratoryRatePlaceholder: 'e.g. 16',
  },

  form: {
    viewHistoryA11y: 'View triage history',
    redFlagsTitle: 'Life-threatening signs',
    redFlagsHint: 'Turn on anything that applies',
    vitalsTitle: 'Vital signs (optional)',
    vitalsHint: 'Leave blank if you do not know',
    painTitle: 'Pain level',
    painHint: '0 = no pain, 10 = worst imaginable',
    painA11y: 'Pain level {level}',
    painSelected: 'Selected: {pain} / 10',
    durationTitle: 'Symptom duration',
    durationHint: 'Optional',
    durationPlaceholder: 'e.g. 6',
    durationA11y: 'Symptom duration in hours',
    durationUnit: 'hours',
    symptomsTitle: 'Other symptoms',
    symptomsHint: 'Select all that apply',
    submit: 'Run triage assessment',
  },

  result: {
    title: 'Triage result',
    recommendedAction: 'Recommended action',
    triggeredTitle: 'What triggered this level',
    noReasons:
      'No red flags, critical vitals, or concerning symptoms were reported. If you feel unwell, stay alert and re-check if symptoms change.',
    callEmergency: 'Call {emergencyNumber}',
    alertTitle: 'Call emergency services',
    alertBody: 'Dial {emergencyNumber} on your phone.',
    startOver: 'Start over',
  },

  history: {
    title: 'Triage history',
    back: '‹ Back',
    delete: 'Delete',
    clearAll: 'Clear all',
    clearAllTitle: 'Clear all history?',
    clearAllBody: 'This permanently deletes all stored triage assessments from this device.',
    cancel: 'Cancel',
    inputSummary: 'Input summary',
    redFlags: 'Red flags: ',
    vitals: 'Vitals: ',
    pain: 'Pain: ',
    painValue: '{pain} / 10',
    duration: 'Duration: ',
    durationValue: '{hours} hours',
    symptoms: 'Symptoms: ',
    noneReported: 'None reported',
    emptyTitle: 'No assessments yet',
    emptyBody:
      'Completed triage assessments are saved on this device so you can review them later. Run an assessment to see it here.',
    runAssessment: 'Run an assessment',
    itemA11y: 'Triage from {date}',
    backToAssessment: 'Back to assessment',
  },

  reason: {
    redFlag: 'Red flag: {label}',
    spo2Critical: 'SpO2 {value}% is below 90%',
    bpCritical: 'Systolic BP {value} mmHg is below 90 or above 200',
    hrCritical: 'Heart rate {value} bpm is below 40 or above 150',
    rrCritical: 'Respiratory rate {value} is below 8 or above 30',
    spo2Borderline: 'SpO2 {value}% is borderline low (90-94%)',
    bpBorderline: 'Systolic BP {value} mmHg is borderline (90-99 or 181-200)',
    hrBorderline: 'Heart rate {value} bpm is borderline (41-49 or 121-150)',
    rrBorderline: 'Respiratory rate {value} is borderline (9-10 or 26-30)',
    highFever: 'Temperature {value}°C indicates high fever (≥39.5°C)',
    hypothermia: 'Temperature {value}°C indicates hypothermia (≤35.0°C)',
    highRiskSymptom: 'High-risk symptom: {label}',
    painSevere: 'Pain score {value}/10 is severe',
    giDehydration: 'GI/dehydration symptom: {label}',
    fracture: 'Suspected fracture: {label}',
    painSignificant: 'Pain score {value}/10 is significant (≥6)',
    durationLong: 'Symptoms have lasted {value} hours (≥48 hours)',
    painMild: 'Pain score {value}/10',
    symptom: 'Symptom: {label}',
  },
} as const;

export type StringCatalog = typeof en;
