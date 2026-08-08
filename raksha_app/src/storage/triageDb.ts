// Local SQLite history for triage results — works offline, never leaves the
// device. All calls are wrapped in try/catch so an unavailable DB (e.g. some
// web builds) degrades to an empty history instead of crashing the screen.
import * as SQLite from 'expo-sqlite';

import type { TriageInput, TriageResult } from '@/types';

export interface TriageHistoryRow {
  id: number;
  created_at: string;
  input: TriageInput;
  result: TriageResult;
}

let db: SQLite.SQLiteDatabase | null = null;

function getDb(): SQLite.SQLiteDatabase | null {
  try {
    if (!db) {
      db = SQLite.openDatabaseSync('triage.db');
      db.execSync(
        `CREATE TABLE IF NOT EXISTS triage_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          input TEXT NOT NULL,
          result TEXT NOT NULL
        )`
      );
    }
    return db;
  } catch {
    return null;
  }
}

export function saveTriage(input: TriageInput, result: TriageResult): void {
  const conn = getDb();
  if (!conn) return;
  try {
    conn.runSync(
      'INSERT INTO triage_history (created_at, input, result) VALUES (?, ?, ?)',
      new Date().toISOString(),
      JSON.stringify(input),
      JSON.stringify(result)
    );
  } catch {
    // history is best-effort
  }
}

export function listTriage(): TriageHistoryRow[] {
  const conn = getDb();
  if (!conn) return [];
  try {
    const rows = conn.getAllSync<{ id: number; created_at: string; input: string; result: string }>(
      'SELECT * FROM triage_history ORDER BY id DESC'
    );
    return rows
      .map((r) => ({
        id: r.id,
        created_at: r.created_at,
        input: JSON.parse(r.input) as TriageInput,
        result: JSON.parse(r.result) as TriageResult,
      }))
      .filter((r) => r.result && typeof r.result.severity === 'number');
  } catch {
    return [];
  }
}

export function deleteTriage(id: number): void {
  const conn = getDb();
  if (!conn) return;
  try {
    conn.runSync('DELETE FROM triage_history WHERE id = ?', id);
  } catch {
    // best-effort
  }
}

export function clearTriage(): void {
  const conn = getDb();
  if (!conn) return;
  try {
    conn.runSync('DELETE FROM triage_history');
  } catch {
    // best-effort
  }
}
