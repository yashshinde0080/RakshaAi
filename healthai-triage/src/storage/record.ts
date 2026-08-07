/**
 * Pure record logic for on-device triage history.
 * Kept free of AsyncStorage so it stays unit-testable in plain node.
 */

import { TriageInput, TriageResult } from '../types';

export interface TriageRecord {
  id: string;
  timestamp: number; // epoch ms
  input: TriageInput;
  result: TriageResult;
}

/** Cap on stored records — prevents unbounded growth of local storage. */
export const MAX_RECORDS = 50;

function newId(now: number): string {
  return `${now.toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function createRecord(
  input: TriageInput,
  result: TriageResult,
  now: number = Date.now(),
): TriageRecord {
  return { id: newId(now), timestamp: now, input, result };
}

/** Newest-first; keeps at most `max` records. */
export function capRecords(records: TriageRecord[], max: number = MAX_RECORDS): TriageRecord[] {
  return [...records].sort((a, b) => b.timestamp - a.timestamp).slice(0, max);
}

export function serializeHistory(records: TriageRecord[]): string {
  return JSON.stringify(records);
}

/** Tolerant parse: garbage or non-array input yields an empty list. */
export function deserializeHistory(raw: string): TriageRecord[] {
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as TriageRecord[]) : [];
  } catch {
    return [];
  }
}
