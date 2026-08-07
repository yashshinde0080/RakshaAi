import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { calculateTriage } from '../src/logic/triageEngine';
import { RedFlags, SeverityLevel, TriageInput } from '../src/types';

function baseInput(overrides: Partial<TriageInput> = {}): TriageInput {
  return {
    ageYears: 30,
    painScore: 0,
    redFlags: {
      unresponsive: false,
      notBreathingOrGasping: false,
      strokeSigns: false,
      chestPainSevere: false,
      uncontrolledBleeding: false,
      anaphylaxisSigns: false,
      seizureActive: false,
    },
    vitals: {},
    otherSymptoms: [],
    ...overrides,
  };
}

const withRedFlag = (key: keyof RedFlags): TriageInput =>
  baseInput({
    redFlags: { ...baseInput().redFlags, [key]: true },
  });

const allRedFlagKeys: Array<keyof RedFlags> = [
  'unresponsive',
  'notBreathingOrGasping',
  'strokeSigns',
  'chestPainSevere',
  'uncontrolledBleeding',
  'anaphylaxisSigns',
  'seizureActive',
];

describe('calculateTriage — red flags (Level 1)', () => {
  for (const key of allRedFlagKeys) {
    it(`any red flag → Level 1 (${key})`, () => {
      const result = calculateTriage(withRedFlag(key));
      assert.equal(result.level, SeverityLevel.LEVEL_1);
      assert.equal(result.isEmergency, true);
      assert.ok(result.triggeredReasons.length > 0);
    });
  }

  it('red flags override everything else (pain 0, no symptoms, no vitals)', () => {
    const result = calculateTriage(withRedFlag('chestPainSevere'));
    assert.equal(result.level, SeverityLevel.LEVEL_1);
  });
});

describe('calculateTriage — critical vitals (Level 1)', () => {
  const criticalCases: Array<[string, Partial<TriageInput['vitals']>]> = [
    ['SpO2 89 (below 90)', { spo2: 89 }],
    ['SpO2 0', { spo2: 0 }],
    ['systolic BP 89 (below 90)', { systolicBP: 89 }],
    ['systolic BP 201 (above 200)', { systolicBP: 201 }],
    ['heart rate 39 (below 40)', { heartRate: 39 }],
    ['heart rate 151 (above 150)', { heartRate: 151 }],
    ['resp rate 7 (below 8)', { respiratoryRate: 7 }],
    ['resp rate 31 (above 30)', { respiratoryRate: 31 }],
  ];

  for (const [name, vitals] of criticalCases) {
    it(`${name} → Level 1`, () => {
      const result = calculateTriage(baseInput({ vitals }));
      assert.equal(result.level, SeverityLevel.LEVEL_1, name);
    });
  }

  it('critical vitals beat emergent signals (SpO2 89 + pain 10 → Level 1)', () => {
    const result = calculateTriage(
      baseInput({ vitals: { spo2: 89 }, painScore: 10 }),
    );
    assert.equal(result.level, SeverityLevel.LEVEL_1);
  });

  it('HR 40 and RR 8 fall between critical and borderline bands (deliberate per TRD §5)', () => {
    // ponytail: TRD §5 draws critical at <40 bpm and <8 breaths/min, borderline
    // starts at 41/9. Exact 40 and 8 are therefore not caught by any check.
    // This test locks that boundary in so a change here is a deliberate decision.
    const hr40 = calculateTriage(baseInput({ vitals: { heartRate: 40 } }));
    assert.notEqual(hr40.level, SeverityLevel.LEVEL_1);
    const rr8 = calculateTriage(baseInput({ vitals: { respiratoryRate: 8 } }));
    assert.notEqual(rr8.level, SeverityLevel.LEVEL_1);
  });
});

describe('calculateTriage — emergent signals (Level 2)', () => {
  const borderlineCases: Array<[string, Partial<TriageInput['vitals']>]> = [
    ['SpO2 90 borderline', { spo2: 90 }],
    ['SpO2 94 borderline', { spo2: 94 }],
    ['systolic BP 90 borderline', { systolicBP: 90 }],
    ['systolic BP 99 borderline', { systolicBP: 99 }],
    ['systolic BP 181 borderline', { systolicBP: 181 }],
    ['systolic BP 200 borderline', { systolicBP: 200 }],
    ['heart rate 41 borderline', { heartRate: 41 }],
    ['heart rate 49 borderline', { heartRate: 49 }],
    ['heart rate 121 borderline', { heartRate: 121 }],
    ['heart rate 150 borderline', { heartRate: 150 }],
    ['resp rate 9 borderline', { respiratoryRate: 9 }],
    ['resp rate 10 borderline', { respiratoryRate: 10 }],
    ['resp rate 26 borderline', { respiratoryRate: 26 }],
    ['resp rate 30 borderline', { respiratoryRate: 30 }],
    ['temp 39.5 high fever', { temperatureC: 39.5 }],
    ['temp 35.0 hypothermia', { temperatureC: 35.0 }],
  ];

  for (const [name, vitals] of borderlineCases) {
    it(`${name} → Level 2`, () => {
      const result = calculateTriage(baseInput({ vitals }));
      assert.equal(result.level, SeverityLevel.LEVEL_2, name);
    });
  }

  it('pain 9 → Level 2', () => {
    const result = calculateTriage(baseInput({ painScore: 9 }));
    assert.equal(result.level, SeverityLevel.LEVEL_2);
  });

  it('pain 10 → Level 2', () => {
    const result = calculateTriage(baseInput({ painScore: 10 }));
    assert.equal(result.level, SeverityLevel.LEVEL_2);
  });

  it('high-risk symptom → Level 2', () => {
    const result = calculateTriage(baseInput({ otherSymptoms: ['chestPain'] }));
    assert.equal(result.level, SeverityLevel.LEVEL_2);
  });

  it('emergent beats urgent (pain 9 + fracture symptom → Level 2)', () => {
    const result = calculateTriage(
      baseInput({ painScore: 9, otherSymptoms: ['suspectedFracture'] }),
    );
    assert.equal(result.level, SeverityLevel.LEVEL_2);
  });

  it('emergent beats urgent (SpO2 92 + duration 96h → Level 2)', () => {
    const result = calculateTriage(
      baseInput({ vitals: { spo2: 92 }, symptomDurationHours: 96 }),
    );
    assert.equal(result.level, SeverityLevel.LEVEL_2);
  });
});

describe('calculateTriage — urgent signals (Level 3)', () => {
  it('pain 6 → Level 3', () => {
    assert.equal(calculateTriage(baseInput({ painScore: 6 })).level, SeverityLevel.LEVEL_3);
  });

  it('pain 8 → Level 3 (below pain 9 emergent threshold)', () => {
    assert.equal(calculateTriage(baseInput({ painScore: 8 })).level, SeverityLevel.LEVEL_3);
  });

  it('duration 48h → Level 3', () => {
    assert.equal(
      calculateTriage(baseInput({ symptomDurationHours: 48 })).level,
      SeverityLevel.LEVEL_3,
    );
  });

  it('duration 100h → Level 3', () => {
    assert.equal(
      calculateTriage(baseInput({ symptomDurationHours: 100 })).level,
      SeverityLevel.LEVEL_3,
    );
  });

  it('GI/dehydration symptom → Level 3', () => {
    for (const symptom of ['vomiting', 'diarrhea', 'dehydrationSigns', 'unableToKeepFluids']) {
      assert.equal(
        calculateTriage(baseInput({ otherSymptoms: [symptom] })).level,
        SeverityLevel.LEVEL_3,
        symptom,
      );
    }
  });

  it('suspected fracture → Level 3', () => {
    const result = calculateTriage(baseInput({ otherSymptoms: ['suspectedFracture'] }));
    assert.equal(result.level, SeverityLevel.LEVEL_3);
  });
});

describe('calculateTriage — less urgent (Level 4)', () => {
  it('pain 3 → Level 4', () => {
    assert.equal(calculateTriage(baseInput({ painScore: 3 })).level, SeverityLevel.LEVEL_4);
  });

  it('pain 5 → Level 4 (below pain 6 urgent threshold)', () => {
    assert.equal(calculateTriage(baseInput({ painScore: 5 })).level, SeverityLevel.LEVEL_4);
  });

  it('plain symptom (fever) → Level 4', () => {
    const result = calculateTriage(baseInput({ otherSymptoms: ['fever'] }));
    assert.equal(result.level, SeverityLevel.LEVEL_4);
  });

  it('plain symptom with no pain → Level 4', () => {
    const result = calculateTriage(baseInput({ otherSymptoms: ['cough'] }));
    assert.equal(result.level, SeverityLevel.LEVEL_4);
  });
});

describe('calculateTriage — default (Level 5)', () => {
  it('empty input → Level 5', () => {
    const result = calculateTriage(baseInput());
    assert.equal(result.level, SeverityLevel.LEVEL_5);
    assert.equal(result.isEmergency, false);
    assert.deepEqual(result.triggeredReasons, []);
  });

  it('pain 0, no symptoms, normal vitals → Level 5', () => {
    const result = calculateTriage(
      baseInput({
        painScore: 0,
        vitals: { heartRate: 72, systolicBP: 120, spo2: 98, temperatureC: 37.0, respiratoryRate: 16 },
        otherSymptoms: [],
      }),
    );
    assert.equal(result.level, SeverityLevel.LEVEL_5);
  });

  it('pain 2 → Level 5 (below pain 3 threshold)', () => {
    assert.equal(calculateTriage(baseInput({ painScore: 2 })).level, SeverityLevel.LEVEL_5);
  });
});

describe('calculateTriage — result integrity', () => {
  it('every reason maps to a checked condition (no free text)', () => {
    const result = calculateTriage(
      baseInput({
        redFlags: { ...baseInput().redFlags, unresponsive: true },
        vitals: { spo2: 92 },
        painScore: 7,
        symptomDurationHours: 60,
        otherSymptoms: ['fever'],
      }),
    );
    assert.equal(result.level, SeverityLevel.LEVEL_1); // red flag short-circuits
    assert.ok(result.triggeredReasons.every((r) => typeof r === 'string' && r.length > 0));
  });

  it('isEmergency is true only for Levels 1-2', () => {
    const cases: Array<{ level: SeverityLevel; input: TriageInput }> = [
      {
        level: SeverityLevel.LEVEL_1,
        input: baseInput({
          redFlags: { ...baseInput().redFlags, strokeSigns: true },
        }),
      },
      {
        level: SeverityLevel.LEVEL_2,
        input: baseInput({ vitals: { spo2: 90 } }),
      },
      {
        level: SeverityLevel.LEVEL_3,
        input: baseInput({ painScore: 6, otherSymptoms: ['vomiting'] }),
      },
      {
        level: SeverityLevel.LEVEL_4,
        input: baseInput({ painScore: 3, otherSymptoms: ['fever'] }),
      },
      {
        level: SeverityLevel.LEVEL_5,
        input: baseInput(),
      },
    ];
    for (const { level, input } of cases) {
      const result = calculateTriage(input);
      assert.equal(result.level, level, `level ${level}`);
      assert.equal(result.isEmergency, level <= SeverityLevel.LEVEL_2, `level ${level}`);
    }
  });

  it('input is not mutated by calculateTriage', () => {
    const input = baseInput({ otherSymptoms: ['fever'] });
    const snapshot = JSON.stringify(input);
    calculateTriage(input);
    assert.equal(JSON.stringify(input), snapshot);
  });
});
