import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { capRecords, createRecord, deserializeHistory, MAX_RECORDS, serializeHistory, TriageRecord } from '../src/storage/record';
import { SeverityLevel, TriageInput, TriageResult } from '../src/types';

function sampleInput(): TriageInput {
  return {
    painScore: 6,
    symptomDurationHours: 60,
    vitals: { spo2: 98 },
    redFlags: {
      unresponsive: false,
      notBreathingOrGasping: false,
      strokeSigns: false,
      chestPainSevere: false,
      uncontrolledBleeding: false,
      anaphylaxisSigns: false,
      seizureActive: false,
    },
    otherSymptoms: ['vomiting'],
  };
}

function sampleResult(): TriageResult {
  return {
    level: SeverityLevel.LEVEL_3,
    label: 'Urgent',
    color: '#D97706',
    recommendedAction: 'Seek medical attention within a few hours.',
    triggeredReasons: ['GI/dehydration symptom: Vomiting'],
    isEmergency: false,
  };
}

describe('createRecord', () => {
  it('stores input, result, and a timestamp', () => {
    const record = createRecord(sampleInput(), sampleResult(), 1234567890);
    assert.equal(record.timestamp, 1234567890);
    assert.deepEqual(record.input, sampleInput());
    assert.deepEqual(record.result, sampleResult());
    assert.ok(record.id.length > 0);
  });

  it('generates unique ids', () => {
    const a = createRecord(sampleInput(), sampleResult(), 1);
    const b = createRecord(sampleInput(), sampleResult(), 1);
    assert.notEqual(a.id, b.id);
  });
});

describe('capRecords', () => {
  function makeRecords(n: number): TriageRecord[] {
    return Array.from({ length: n }, (_, i) =>
      createRecord(sampleInput(), sampleResult(), i),
    );
  }

  it('keeps newest-first order and trims to MAX_RECORDS', () => {
    const trimmed = capRecords(makeRecords(MAX_RECORDS + 10));
    assert.equal(trimmed.length, MAX_RECORDS);
    assert.equal(trimmed[0].timestamp, MAX_RECORDS + 9); // newest first
  });

  it('does not grow lists under the cap', () => {
    const records = makeRecords(3);
    assert.equal(capRecords(records).length, 3);
  });
});

describe('serialize/deserialize history', () => {
  it('round-trips records through JSON', () => {
    const records = [createRecord(sampleInput(), sampleResult(), 1000)];
    const restored = deserializeHistory(serializeHistory(records));
    assert.deepEqual(restored, records);
  });

  it('returns empty array for garbage input', () => {
    assert.deepEqual(deserializeHistory('not json'), []);
  });

  it('returns empty array for non-array JSON', () => {
    assert.deepEqual(deserializeHistory('{"a":1}'), []);
  });
});
