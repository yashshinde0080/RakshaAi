import assert from 'node:assert/strict';
import test from 'node:test';

import { en, t, StringKey, StringParams } from '../src/i18n';

/** Flatten the nested catalog to [dottedKey, string] leaf pairs. */
function leafStrings(
  obj: Record<string, unknown>,
  prefix = '',
): Array<[string, string]> {
  const out: Array<[string, string]> = [];
  for (const [key, value] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      out.push([full, value]);
    } else if (value && typeof value === 'object') {
      out.push(...leafStrings(value as Record<string, unknown>, full));
    }
  }
  return out;
}

test('t interpolates {param} placeholders', () => {
  assert.equal(t('reason.spo2Critical', { value: 89 }), 'SpO2 89% is below 90%');
  assert.equal(t('reason.painSevere', { value: 9 }), 'Pain score 9/10 is severe');
  assert.equal(
    t('disclaimer.body', { emergencyNumber: '112' }),
    'This tool offers guidance only and does not replace professional medical care. If this is a life-threatening emergency, call 112 immediately.',
  );
});

test('t returns the raw string when no params are needed', () => {
  assert.equal(t('common.history'), 'History');
  assert.equal(t('form.submit'), 'Run triage assessment');
});

test('t handles numeric and string params uniformly', () => {
  assert.equal(t('severity.levelName', { level: 1 }), 'Level 1');
  assert.equal(t('history.durationValue', { hours: 6 }), '6 hours');
});

test('every param-bearing string in the catalog renders clean with sample params', () => {
  const sample: StringParams = {
    label: 'X',
    value: 42,
    level: 3,
    hours: 6,
    pain: 4,
    date: 'now',
    emergencyNumber: '112',
  };
  const leaf = leafStrings(en as unknown as Record<string, unknown>);
  assert.ok(leaf.length > 50, `catalog looks too small: ${leaf.length} strings`);
  for (const [key, value] of leaf) {
    if (value.includes('{')) {
      const rendered = t(key as StringKey, sample);
      assert.ok(!rendered.includes('{'), `unrendered placeholder left in "${key}": ${rendered}`);
    }
  }
});

test('catalog strings have no accidental double spaces (translation hygiene)', () => {
  for (const [key, value] of leafStrings(en as unknown as Record<string, unknown>)) {
    assert.ok(!value.includes('  '), `"${key}" contains a double space`);
  }
});

// Type-level param assertions live in tests/i18n.types.ts (enforced by
// `npm run typecheck`, not by the runtime runner).
