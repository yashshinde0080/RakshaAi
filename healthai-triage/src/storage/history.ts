/**
 * AsyncStorage-backed triage history. Fully offline — data never leaves the device.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import { deserializeHistory, serializeHistory, TriageRecord } from './record';

const STORAGE_KEY = '@healthai-triage/history/v1';

export async function loadHistory(): Promise<TriageRecord[]> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  return raw ? deserializeHistory(raw) : [];
}

export async function persistHistory(records: TriageRecord[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, serializeHistory(records));
}
