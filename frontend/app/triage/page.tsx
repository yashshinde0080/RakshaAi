'use client';

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  HeartPulse,
  Phone,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { BrandMark } from '@/components/BrandMark';
import { api } from '@/lib/api';
import { errMsg } from '@/lib/utils';
import type { TriageInput, TriageResult } from '@/types';

// Region-configurable emergency number (config, not hardcoded per region).
const EMERGENCY_NUMBER = '112';

const SEVERITY_COLORS: Record<number, { bg: string; text: string }> = {
  1: { bg: '#dc2626', text: '#ffffff' },
  2: { bg: '#ea580c', text: '#ffffff' },
  3: { bg: '#d97706', text: '#ffffff' },
  4: { bg: '#65a30d', text: '#ffffff' },
  5: { bg: '#16a34a', text: '#ffffff' },
};

// Mirrors the backend Vitals Validator so impossible vitals never leave the
// console — the same hard front gate runs on both ends.
const VITAL_BOUNDS: { key: keyof TriageInput['vitals']; label: string; lo: number; hi: number }[] = [
  { key: 'heart_rate', label: 'Heart rate (bpm)', lo: 20, hi: 250 },
  { key: 'systolic_bp', label: 'Systolic BP (mmHg)', lo: 40, hi: 300 },
  { key: 'spo2', label: 'SpO2 (%)', lo: 50, hi: 100 },
  { key: 'temperature_c', label: 'Temperature (°C)', lo: 30, hi: 45 },
  { key: 'respiratory_rate', label: 'Respiratory rate', lo: 4, hi: 80 },
];

const RED_FLAGS: { key: keyof TriageInput['red_flags']; label: string }[] = [
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
  vitals: Record<string, string>;
  gender: TriageInput['vitals']['gender'] | '';
  flags: TriageInput['red_flags'];
  symptoms: string[];
}

const EMPTY_FORM: FormState = {
  age: '',
  pain: 0,
  duration: '',
  vitals: { heart_rate: '', systolic_bp: '', spo2: '', temperature_c: '', respiratory_rate: '' },
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

const HISTORY_KEY = 'raksha.triage.history.v1';

interface HistoryRow {
  id: number;
  created_at: string;
  input: TriageInput;
  result: TriageResult;
}

function loadHistory(): HistoryRow[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const rows = JSON.parse(raw) as HistoryRow[];
    return rows.filter((r) => r?.result && typeof r.result.severity === 'number');
  } catch {
    return [];
  }
}

function saveHistory(rows: HistoryRow[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(rows.slice(0, 50)));
  } catch {
    // best-effort
  }
}

function validateForm(f: FormState): string[] {
  const errors: string[] = [];
  const num = (s: string): number | undefined =>
    s.trim() === '' ? undefined : Number(s);

  for (const { key, label, lo, hi } of VITAL_BOUNDS) {
    const v = num(f.vitals[key]);
    if (v !== undefined && (Number.isNaN(v) || v < lo || v > hi)) {
      errors.push(`${label} must be ${lo}-${hi}`);
    }
  }
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
      heart_rate: num(f.vitals.heart_rate),
      systolic_bp: num(f.vitals.systolic_bp),
      spo2: num(f.vitals.spo2),
      temperature_c: num(f.vitals.temperature_c),
      respiratory_rate: num(f.vitals.respiratory_rate),
      gender: f.gender === '' ? undefined : f.gender,
    },
    red_flags: f.flags,
    symptoms: f.symptoms,
  };
}

function SourceLabel(source: TriageResult['source']) {
  if (source === 'rules') return 'rule engine';
  if (source === 'llm_retry') return 'AI model (retry)';
  return 'AI model';
}

export default function TriagePage() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [result, setResult] = useState<TriageResult | null>(null);
  const [resultKey, setResultKey] = useState(0);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reloadHistory = useCallback(() => setHistory(loadHistory()), []);
  useEffect(() => reloadHistory(), [reloadHistory]);

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));
  const setVital = (key: string, value: string) =>
    setForm((f) => ({ ...f, vitals: { ...f.vitals, [key]: value } }));
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
      const res = await api.runTriage(input);
      setResult(res);
      setResultKey((k) => k + 1);
      const rows = [{ id: Date.now(), created_at: new Date().toISOString(), input, result: res }, ...loadHistory()];
      saveHistory(rows);
      setHistory(rows);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setRunning(false);
    }
  };

  const clearHistory = () => {
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch {
      // best-effort
    }
    setHistory([]);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Hero */}
      <Card className="relative overflow-hidden border-brand/30 bg-gradient-to-br from-brand/10 via-card to-card">
        <div className="absolute -top-20 -right-20 h-48 w-48 rounded-full bg-brand/10 blur-3xl" />
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center gap-3">
            <BrandMark size={40} />
            <div>
              <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                Raksha Triage
                <Badge variant="outline" className="text-brand border-brand/40">
                  ESI Protocol
                </Badge>
              </h1>
              <p className="text-sm text-muted-foreground">
                Decision-support aid only. In an emergency call {EMERGENCY_NUMBER} immediately.
              </p>
            </div>
          </div>

          {/* Two-agent safety pipeline */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <PipelineStep icon={ShieldCheck} label="Vitals Validator" detail="impossible vitals rejected first" />
            <Chevron />
            <PipelineStep icon={Sparkles} label="Triage Agent" detail="local model, strict ESI JSON" />
            <Chevron />
            <PipelineStep icon={ShieldAlert} label="Safety Gate" detail="schema re-check · retry · rule fallback" />
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Red flags */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Red flags
            </CardTitle>
            <CardDescription className="text-xs">
              Any red flag jumps the result to level 1.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {RED_FLAGS.map((flag) => (
              <div
                key={flag.key}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 bg-muted/30"
              >
                <span className="text-sm">{flag.label}</span>
                <Switch
                  checked={form.flags[flag.key]}
                  onCheckedChange={() => toggleFlag(flag.key)}
                  className="data-[state=checked]:bg-destructive"
                />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Vitals + pain + duration */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                Vitals
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              {VITAL_BOUNDS.map(({ key, label }) => (
                <div key={key} className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">{label}</Label>
                  <Input
                    inputMode="numeric"
                    placeholder="—"
                    value={form.vitals[key]}
                    onChange={(e) => setVital(key, e.target.value)}
                    className="bg-muted/30"
                  />
                </div>
              ))}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Age (years)</Label>
                <Input
                  inputMode="numeric"
                  placeholder="30"
                  value={form.age}
                  onChange={(e) => set({ age: e.target.value })}
                  className="bg-muted/30"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Symptom duration (hours)</Label>
                <Input
                  inputMode="numeric"
                  placeholder="2"
                  value={form.duration}
                  onChange={(e) => set({ duration: e.target.value })}
                  className="bg-muted/30"
                />
              </div>
              <div className="col-span-2 space-y-1.5">
                <Label className="text-xs text-muted-foreground">Gender</Label>
                <div className="flex flex-wrap gap-2">
                  {GENDER_OPTIONS.map((g) => {
                    const active = form.gender === g.value;
                    return (
                      <button
                        key={g.value}
                        type="button"
                        aria-pressed={active}
                        onClick={() => set({ gender: active ? '' : g.value })}
                        className={
                          active
                            ? 'rounded-full border border-brand bg-brand/15 px-3 py-1 text-xs font-medium text-brand'
                            : 'rounded-full border border-border bg-muted/30 px-3 py-1 text-xs text-muted-foreground hover:border-brand/40 hover:text-foreground transition-colors'
                        }
                      >
                        {g.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                Pain level
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">0 — no pain</span>
                <Badge variant="outline" className="text-sm font-bold">{form.pain}</Badge>
                <span className="text-xs text-muted-foreground">10 — worst</span>
              </div>
              <Slider
                value={[form.pain]}
                min={0}
                max={10}
                step={1}
                onValueChange={([v]) => set({ pain: v ?? 0 })}
                className="[&_[role=slider]]:bg-brand"
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Symptoms */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Symptoms
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {SYMPTOM_GROUPS.map((group) => (
            <div key={group.title} className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground">{group.title}</p>
              <div className="flex flex-wrap gap-2">
                {group.items.map((s) => {
                  const active = form.symptoms.includes(s.id);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => toggleSymptom(s.id)}
                      className={
                        active
                          ? 'rounded-full border border-brand bg-brand/15 px-3 py-1 text-xs font-medium text-brand'
                          : 'rounded-full border border-border bg-muted/30 px-3 py-1 text-xs text-muted-foreground hover:border-brand/40 hover:text-foreground transition-colors'
                      }
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Run */}
      <Button
        onClick={submit}
        disabled={running}
        size="lg"
        className="w-full bg-brand hover:bg-brand/90 text-white disabled:opacity-60"
      >
        {running ? (
          <>
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            Running safety pipeline…
          </>
        ) : (
          <>
            <HeartPulse className="h-4 w-4" />
            Run Triage
          </>
        )}
      </Button>

      {/* Result */}
      {result && <ResultCard key={resultKey} result={result} />}

      {/* History */}
      <Card>
        <CardHeader className="pb-3 flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              History
            </CardTitle>
            <CardDescription className="text-xs">
              Stored locally in this browser only — nothing leaves the device.
            </CardDescription>
          </div>
          {history.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearHistory} className="text-muted-foreground">
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Clear
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">No past assessments yet.</p>
          ) : (
            <div className="space-y-2">
              {history.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => {
                    setResult(row.result);
                    setResultKey((k) => k + 1);
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2.5 text-left hover:border-brand/40 transition-colors"
                >
                  <span className="text-sm font-medium">
                    Level {row.result.severity} · {row.result.label}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(row.created_at).toLocaleString()} · via {SourceLabel(row.result.source)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Subcomponents ───────────────────────────────────────────────────────────

function PipelineStep({
  icon: Icon,
  label,
  detail,
}: {
  icon: typeof ShieldCheck;
  label: string;
  detail: string;
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand/5 px-3 py-1.5">
      <Icon className="h-3.5 w-3.5 text-brand" />
      <span className="font-semibold">{label}</span>
      <span className="text-muted-foreground hidden sm:inline">— {detail}</span>
    </div>
  );
}

function Chevron() {
  return <span className="text-muted-foreground select-none">→</span>;
}

function ResultCard({ result }: { result: TriageResult }) {
  const color = SEVERITY_COLORS[result.severity] ?? SEVERITY_COLORS[5];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <Card className="overflow-hidden border-brand/30">
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center justify-between gap-4 p-6">
            <div className="flex items-center gap-4">
              <div
                className="flex h-16 w-16 items-center justify-center rounded-2xl text-lg font-bold shadow-lg"
                style={{ backgroundColor: color.bg, color: color.text }}
              >
                {result.severity}
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  ESI Level {result.severity}
                </p>
                <h2 className="text-xl font-bold tracking-tight">{result.label}</h2>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="outline">
                via {SourceLabel(result.source)}
                {result.validation.retries > 0 ? ` · retried ${result.validation.retries}x` : ''}
              </Badge>
              {result.over_triage && (
                <Badge className="bg-amber-500/15 text-amber-600 border-amber-500/40">
                  over-triaged by AI (rule level lower)
                </Badge>
              )}
              {result.escalated && (
                <Badge className="bg-destructive/15 text-destructive border-destructive/40">
                  raised to rule level for safety
                </Badge>
              )}
              {!result.validation.schema_ok && (
                <Badge variant="secondary">schema re-check failed → rules</Badge>
              )}
            </div>
          </div>

          <div className="space-y-3 border-t border-border bg-muted/20 p-6">
            <p className="text-sm leading-relaxed">{result.recommended_action}</p>

            {result.red_flags.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-wider text-destructive">Red flags</p>
                {result.red_flags.map((r, i) => (
                  <p key={i} className="text-sm text-muted-foreground">• {r}</p>
                ))}
              </div>
            )}

            {result.reasons.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Why</p>
                {result.reasons.map((r, i) => (
                  <p key={i} className="text-sm text-muted-foreground">• {r}</p>
                ))}
              </div>
            )}

            {result.is_emergency && (
              <a
                href={`tel:${EMERGENCY_NUMBER}`}
                className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-destructive/90"
              >
                <Phone className="h-4 w-4" />
                Call {EMERGENCY_NUMBER} now
              </a>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
