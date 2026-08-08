import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import {
  activateAgent,
  createAgent,
  deactivateAllAgents,
  deleteAgent,
  errMsg,
  getAllSettings,
  listAgents,
  setParentalPin,
  setSecurityPassword,
  updateAgent,
  updateSettingsSection,
} from '@/api';
import type { Agent, SettingsMap } from '@/types';

const AGENT_ROLES = [
  'doctor', 'engineer', 'lawyer', 'teacher', 'scientist', 'writer', 'therapist',
  'financial_advisor', 'chef', 'fitness_trainer', 'data_analyst', 'marketing_expert',
  'cybersecurity_expert', 'historian', 'philosopher', 'custom',
];

const TONES = ['professional', 'casual', 'formal', 'friendly', 'concise', 'detailed', 'academic', 'creative'];
const CHARACTERISTICS = [
  'warm', 'enthusiastic', 'cynical', 'humorous', 'direct', 'empathetic', 'analytical',
  'encouraging', 'sarcastic',
];
const RETENTION = ['session_only', '1_day', '7_days', '30_days', '90_days', 'indefinite'];
const FILTER_LEVELS = ['off', 'low', 'medium', 'high', 'strict'];
const THEMES = ['light', 'dark', 'system'];
const LANGUAGES = ['en', 'es', 'fr', 'de', 'ja', 'zh', 'hi', 'ar', 'pt', 'ru'];

export default function SettingsScreen() {
  const [settings, setSettings] = useState<SettingsMap>({});
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, a] = await Promise.all([getAllSettings(), listAgents()]);
      setSettings(s);
      setAgents(a);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const saveSection = async (section: string, data: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await updateSettingsSection(section, data);
      setSavedMsg(`${section.replace(/_/g, ' ')} saved`);
      setTimeout(() => setSavedMsg(null), 2500);
      await refresh();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const general = (settings.general ?? {}) as Record<string, unknown>;
  const personalization = (settings.personalization ?? {}) as Record<string, unknown>;
  const dataControls = (settings.data_controls ?? {}) as Record<string, unknown>;
  const security = (settings.security ?? {}) as Record<string, unknown>;
  const parental = (settings.parental_controls ?? {}) as Record<string, unknown>;
  const project = (settings.project ?? {}) as Record<string, unknown>;

  return (
    <SafeAreaView style={styles.flex} edges={['top']}>
      <ScrollView contentContainerStyle={styles.list}>
        <ThemedText type="subtitle">Settings</ThemedText>
        {error && <ErrorBanner message={error} />}
        {savedMsg && (
          <ThemedText type="small" themeColor="textSecondary">
            ✓ {savedMsg}
          </ThemedText>
        )}

        <ProjectSection project={project} />

        <AgentSection
          agents={agents}
          busy={busy}
          onActivate={async (id) => {
            try {
              await activateAgent(id);
              await refresh();
            } catch (e) {
              setError(errMsg(e));
            }
          }}
          onDeactivateAll={async () => {
            try {
              await deactivateAllAgents();
              await refresh();
            } catch (e) {
              setError(errMsg(e));
            }
          }}
          onSave={async (agent, isNew) => {
            try {
              if (isNew) await createAgent(agent);
              else await updateAgent(agent.id, agent);
              await refresh();
            } catch (e) {
              setError(errMsg(e));
            }
          }}
          onDelete={async (id) => {
            try {
              await deleteAgent(id);
              await refresh();
            } catch (e) {
              setError(errMsg(e));
            }
          }}
        />

        <Section title="General" onSave={() => saveSection('general', general)} busy={busy}>
          <OptionRow label="Theme" value={String(general.theme ?? 'dark')} options={THEMES}
            onChange={(v) => setSettings({ ...settings, general: { ...general, theme: v } })} />
          <OptionRow label="Language" value={String(general.language ?? 'en')} options={LANGUAGES}
            onChange={(v) => setSettings({ ...settings, general: { ...general, language: v } })} />
          <SwitchRow label="Stream responses" value={!!general.stream_responses}
            onChange={(v) => setSettings({ ...settings, general: { ...general, stream_responses: v } })} />
          <NumberRow label="Max context length" value={String(general.max_context_length ?? 4096)}
            onChange={(v) => setSettings({ ...settings, general: { ...general, max_context_length: Number(v) || 4096 } })} />
        </Section>

        <Section title="Personalization" onSave={() => saveSection('personalization', personalization)} busy={busy}>
          <OptionRow label="Style tone" value={String(personalization.base_style_tone ?? 'professional')} options={TONES}
            onChange={(v) => setSettings({ ...settings, personalization: { ...personalization, base_style_tone: v } })} />
          <MultiChips label="Characteristics" selected={(personalization.characteristics as string[]) ?? []}
            options={CHARACTERISTICS}
            onToggle={(v) => {
              const cur = (personalization.characteristics as string[]) ?? [];
              const next = cur.includes(v) ? cur.filter((c) => c !== v) : [...cur, v];
              setSettings({ ...settings, personalization: { ...personalization, characteristics: next } });
            }} />
          <TextAreaRow label="Custom instructions" value={String(personalization.custom_instructions ?? '')}
            onChange={(v) => setSettings({ ...settings, personalization: { ...personalization, custom_instructions: v } })} />
          <TextFieldRow label="Preferred name" value={String(personalization.preferred_name ?? '')}
            onChange={(v) => setSettings({ ...settings, personalization: { ...personalization, preferred_name: v } })} />
        </Section>

        <Section title="Data Controls" onSave={() => saveSection('data_controls', dataControls)} busy={busy}>
          <SwitchRow label="Save chat history" value={!!dataControls.save_chat_history}
            onChange={(v) => setSettings({ ...settings, data_controls: { ...dataControls, save_chat_history: v } })} />
          <OptionRow label="Data retention" value={String(dataControls.data_retention ?? '30_days')} options={RETENTION}
            onChange={(v) => setSettings({ ...settings, data_controls: { ...dataControls, data_retention: v } })} />
          <SwitchRow label="Encrypt local data" value={!!dataControls.encrypt_local_data}
            onChange={(v) => setSettings({ ...settings, data_controls: { ...dataControls, encrypt_local_data: v } })} />
          <SwitchRow label="Clear on exit" value={!!dataControls.clear_on_exit}
            onChange={(v) => setSettings({ ...settings, data_controls: { ...dataControls, clear_on_exit: v } })} />
        </Section>

        <Section title="Security" onSave={() => saveSection('security', security)} busy={busy}>
          <SwitchRow label="Require password" value={!!security.require_password}
            onChange={(v) => setSettings({ ...settings, security: { ...security, require_password: v } })} />
          <SwitchRow label="Encrypt models" value={!!security.encrypt_models}
            onChange={(v) => setSettings({ ...settings, security: { ...security, encrypt_models: v } })} />
          <SwitchRow label="Bind localhost only" value={!!security.bind_localhost_only}
            onChange={(v) => setSettings({ ...settings, security: { ...security, bind_localhost_only: v } })} />
          <SwitchRow label="Audit logging" value={!!security.audit_logging}
            onChange={(v) => setSettings({ ...settings, security: { ...security, audit_logging: v } })} />
          <SecretRow label="Set password (min 6 chars)" placeholder="New password"
            onSubmit={async (v) => {
              try {
                await setSecurityPassword(v);
                setSavedMsg('password set');
                setTimeout(() => setSavedMsg(null), 2500);
              } catch (e) {
                setError(errMsg(e));
              }
            }} />
        </Section>

        <Section title="Parental Controls" onSave={() => saveSection('parental_controls', parental)} busy={busy}>
          <SwitchRow label="Enabled" value={!!parental.enabled}
            onChange={(v) => setSettings({ ...settings, parental_controls: { ...parental, enabled: v } })} />
          <OptionRow label="Content filter" value={String(parental.content_filter_level ?? 'off')} options={FILTER_LEVELS}
            onChange={(v) => setSettings({ ...settings, parental_controls: { ...parental, content_filter_level: v } })} />
          <SwitchRow label="Block explicit content" value={!!parental.block_explicit_content}
            onChange={(v) => setSettings({ ...settings, parental_controls: { ...parental, block_explicit_content: v } })} />
          <SecretRow label="Set PIN (min 4 digits)" placeholder="New PIN"
            onSubmit={async (v) => {
              try {
                await setParentalPin(v);
                setSavedMsg('PIN set');
                setTimeout(() => setSavedMsg(null), 2500);
              } catch (e) {
                setError(errMsg(e));
              }
            }} />
        </Section>

        {loading && (
          <ThemedView style={styles.loadingRow}>
            <ActivityIndicator size="small" />
          </ThemedView>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Building blocks ─────────────────────────────────────────────────────────

function Section({
  title,
  onSave,
  busy,
  children,
}: {
  title: string;
  onSave: () => void;
  busy: boolean;
  children: React.ReactNode;
}) {
  const theme = useTheme();
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        {title}
      </ThemedText>
      {children}
      <Pressable
        onPress={onSave}
        disabled={busy}
        style={({ pressed }) => [
          styles.saveButton,
          { backgroundColor: theme.backgroundSelected },
          (pressed || busy) && styles.pressed,
        ]}>
        <ThemedText type="smallBold">Save</ThemedText>
      </Pressable>
    </ThemedView>
  );
}

function SwitchRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  const theme = useTheme();
  return (
    <ThemedView style={styles.row}>
      <ThemedText type="small" style={styles.rowLabel}>
        {label}
      </ThemedText>
      <Switch value={value} onValueChange={onChange} trackColor={{ true: theme.textSecondary }} />
    </ThemedView>
  );
}

function TextFieldRow({
  label,
  value,
  onChange,
  keyboardType,
  placeholder,
  secure,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  keyboardType?: 'numeric';
  placeholder?: string;
  secure?: boolean;
}) {
  const theme = useTheme();
  return (
    <ThemedView style={styles.row}>
      <ThemedText type="small" style={styles.rowLabel}>
        {label}
      </ThemedText>
      <TextInput
        style={[styles.fieldInput, { color: theme.text, backgroundColor: theme.background }]}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={theme.textSecondary}
        keyboardType={keyboardType}
        secureTextEntry={secure}
      />
    </ThemedView>
  );
}

function NumberRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return <TextFieldRow label={label} value={value} onChange={onChange} keyboardType="numeric" />;
}

function TextAreaRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const theme = useTheme();
  return (
    <ThemedView style={styles.column}>
      <ThemedText type="small">{label}</ThemedText>
      <TextInput
        style={[styles.fieldInput, styles.textArea, { color: theme.text, backgroundColor: theme.background }]}
        value={value}
        onChangeText={onChange}
        multiline
        placeholderTextColor={theme.textSecondary}
      />
    </ThemedView>
  );
}

function OptionRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const theme = useTheme();
  return (
    <ThemedView style={styles.row}>
      <ThemedText type="small" style={styles.rowLabel}>
        {label}
      </ThemedText>
      <Pressable
        onPress={() => setOpen(true)}
        style={({ pressed }) => [styles.optionButton, { backgroundColor: theme.background }, pressed && styles.pressed]}>
        <ThemedText type="small">{value}</ThemedText>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setOpen(false)}>
          <ThemedView type="backgroundElement" style={styles.modalSheet}>
            <ThemedText type="smallBold" style={styles.cardTitle}>
              {label}
            </ThemedText>
            {options.map((opt) => (
              <Pressable
                key={opt}
                onPress={() => {
                  onChange(opt);
                  setOpen(false);
                }}
                style={({ pressed }) => [
                  styles.optionItem,
                  opt === value && { backgroundColor: theme.backgroundSelected },
                  pressed && styles.pressed,
                ]}>
                <ThemedText type="small">{opt}</ThemedText>
              </Pressable>
            ))}
          </ThemedView>
        </Pressable>
      </Modal>
    </ThemedView>
  );
}

function MultiChips({
  label,
  selected,
  options,
  onToggle,
}: {
  label: string;
  selected: string[];
  options: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <ThemedView style={styles.column}>
      <ThemedText type="small">{label}</ThemedText>
      <ThemedView style={styles.chips}>
        {options.map((opt) => {
          const on = selected.includes(opt);
          return (
            <Pressable key={opt} onPress={() => onToggle(opt)} style={({ pressed }) => pressed && styles.pressed}>
              <ThemedView type={on ? 'backgroundSelected' : 'background'} style={styles.chip}>
                <ThemedText type="small">{opt}</ThemedText>
              </ThemedView>
            </Pressable>
          );
        })}
      </ThemedView>
    </ThemedView>
  );
}

function SecretRow({
  label,
  placeholder,
  onSubmit,
}: {
  label: string;
  placeholder: string;
  onSubmit: (v: string) => Promise<void>;
}) {
  const theme = useTheme();
  const [value, setValue] = useState('');
  const [sending, setSending] = useState(false);
  const submit = async () => {
    if (!value.trim()) return;
    setSending(true);
    await onSubmit(value.trim());
    setSending(false);
    setValue('');
  };
  return (
    <ThemedView style={styles.column}>
      <ThemedText type="small">{label}</ThemedText>
      <ThemedView style={styles.row}>
        <TextInput
          style={[styles.fieldInput, { color: theme.text, backgroundColor: theme.background, flex: 1 }]}
          value={value}
          onChangeText={setValue}
          placeholder={placeholder}
          placeholderTextColor={theme.textSecondary}
          secureTextEntry
        />
        <Pressable
          onPress={submit}
          disabled={sending || !value.trim()}
          style={({ pressed }) => [
            styles.saveButton,
            { backgroundColor: theme.backgroundSelected },
            (pressed || sending || !value.trim()) && styles.pressed,
          ]}>
          {sending ? <ActivityIndicator size="small" /> : <ThemedText type="smallBold">Set</ThemedText>}
        </Pressable>
      </ThemedView>
    </ThemedView>
  );
}

function ProjectSection({ project }: { project: Record<string, unknown> }) {
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold" style={styles.cardTitle}>
        Project
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {String(project.project_name ?? 'Raksha AI')} v{String(project.project_version ?? '')}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {String(project.project_description ?? '')}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {String(project.author ?? '')}
      </ThemedText>
    </ThemedView>
  );
}

// ── Agents ──────────────────────────────────────────────────────────────────

function AgentSection({
  agents,
  busy,
  onActivate,
  onDeactivateAll,
  onSave,
  onDelete,
}: {
  agents: Agent[];
  busy: boolean;
  onActivate: (id: string) => Promise<void>;
  onDeactivateAll: () => Promise<void>;
  onSave: (agent: Agent, isNew: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const theme = useTheme();
  const [editor, setEditor] = useState<{ open: boolean; agent: Agent | null }>({ open: false, agent: null });

  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedView style={styles.rowBetween}>
        <ThemedText type="smallBold">Agents</ThemedText>
        <ThemedView style={styles.row}>
          <Pressable onPress={onDeactivateAll} hitSlop={8} style={({ pressed }) => pressed && styles.pressed}>
            <ThemedText type="small" themeColor="textSecondary">
              Deactivate all
            </ThemedText>
          </Pressable>
          <Pressable
            onPress={() => setEditor({ open: true, agent: null })}
            style={({ pressed }) => [styles.saveButton, { backgroundColor: theme.backgroundSelected }, pressed && styles.pressed]}>
            <ThemedText type="smallBold">New</ThemedText>
          </Pressable>
        </ThemedView>
      </ThemedView>

      {agents.length === 0 && (
        <ThemedText type="small" themeColor="textSecondary">
          No agents yet. Create one to give the model a persona.
        </ThemedText>
      )}
      {agents.map((agent) => (
        <ThemedView key={agent.id} type="background" style={styles.agentRow}>
          <ThemedView style={styles.agentInfo}>
            <ThemedText type="smallBold" numberOfLines={1}>
              {agent.name} {agent.is_active ? '· active' : ''}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary" numberOfLines={2}>
              {agent.description || agent.role}
            </ThemedText>
          </ThemedView>
          <ThemedView style={styles.row}>
            <Pressable
              onPress={() => onActivate(agent.id)}
              disabled={busy}
              hitSlop={8}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" themeColor="textSecondary">
                Activate
              </ThemedText>
            </Pressable>
            <Pressable
              onPress={() => setEditor({ open: true, agent })}
              hitSlop={8}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" themeColor="textSecondary">
                Edit
              </ThemedText>
            </Pressable>
            <Pressable
              onPress={() =>
                Alert.alert('Delete agent', `Delete "${agent.name}"?`, [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Delete', style: 'destructive', onPress: () => onDelete(agent.id) },
                ])
              }
              hitSlop={8}
              style={({ pressed }) => pressed && styles.pressed}>
              <ThemedText type="small" style={{ color: theme.error }}>
                Delete
              </ThemedText>
            </Pressable>
          </ThemedView>
        </ThemedView>
      ))}

      <AgentEditor
        visible={editor.open}
        agent={editor.agent}
        onClose={() => setEditor({ open: false, agent: null })}
        onSave={async (agent, isNew) => {
          await onSave(agent, isNew);
          setEditor({ open: false, agent: null });
        }}
      />
    </ThemedView>
  );
}

function AgentEditor({
  visible,
  agent,
  onClose,
  onSave,
}: {
  visible: boolean;
  agent: Agent | null;
  onClose: () => void;
  onSave: (agent: Agent, isNew: boolean) => Promise<void>;
}) {
  const theme = useTheme();
  const [draft, setDraft] = useState<Agent | null>(null);

  useEffect(() => {
    if (visible) {
      setDraft(
        agent ?? {
          id: `agent-${Date.now()}`,
          name: '',
          role: 'custom',
          description: '',
          system_instruction: '',
          is_active: false,
          icon: 'bot',
          temperature: 0.7,
          max_tokens: 2048,
          enabled: true,
        }
      );
    }
  }, [visible, agent]);

  if (!visible || !draft) return null;

  const set = (patch: Partial<Agent>) => setDraft({ ...draft, ...patch });

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.modalBackdrop} onPress={onClose}>
        <Pressable style={styles.editorSheet} onPress={() => {}}>
          <ThemedView type="backgroundElement" style={styles.editorBody}>
            <ScrollView contentContainerStyle={styles.editorScroll}>
              <ThemedText type="smallBold" style={styles.cardTitle}>
                {agent ? 'Edit agent' : 'New agent'}
              </ThemedText>
              <TextFieldRow label="Name" value={draft.name} onChange={(v) => set({ name: v })} />
              <OptionRow label="Role" value={draft.role} options={AGENT_ROLES} onChange={(v) => set({ role: v })} />
              <TextFieldRow
                label="Icon"
                value={draft.icon}
                onChange={(v) => set({ icon: v })}
                placeholder="bot"
              />
              <NumberRow label="Temperature (0–2)" value={String(draft.temperature)} onChange={(v) => set({ temperature: Number(v) || 0.7 })} />
              <NumberRow label="Max tokens" value={String(draft.max_tokens)} onChange={(v) => set({ max_tokens: Number(v) || 2048 })} />
              <TextAreaRow label="Description" value={draft.description} onChange={(v) => set({ description: v })} />
              <TextAreaRow label="System instruction" value={draft.system_instruction} onChange={(v) => set({ system_instruction: v })} />
            </ScrollView>
            <ThemedView style={styles.editorActions}>
              <Pressable
                onPress={onClose}
                style={({ pressed }) => [
                  styles.saveButton,
                  { backgroundColor: theme.background },
                  pressed && styles.pressed,
                ]}>
                <ThemedText type="smallBold">Cancel</ThemedText>
              </Pressable>
              <Pressable
                onPress={() => onSave(draft, !agent)}
                disabled={!draft.name.trim()}
                style={({ pressed }) => [
                  styles.saveButton,
                  { backgroundColor: theme.backgroundSelected },
                  (pressed || !draft.name.trim()) && styles.pressed,
                ]}>
                <ThemedText type="smallBold">Save</ThemedText>
              </Pressable>
            </ThemedView>
          </ThemedView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  list: {
    padding: Spacing.three,
    paddingBottom: BottomTabInset,
    gap: Spacing.three,
  },
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTitle: {
    marginBottom: Spacing.one,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  rowBetween: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  rowLabel: {
    flex: 1,
  },
  column: {
    gap: Spacing.one,
  },
  fieldInput: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 15,
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  saveButton: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.three,
    alignItems: 'center',
    minHeight: 34,
    justifyContent: 'center',
  },
  optionButton: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  chip: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: '#0008',
    justifyContent: 'center',
    padding: Spacing.four,
  },
  modalSheet: {
    borderRadius: Spacing.three,
    padding: Spacing.four,
    gap: Spacing.one,
    maxHeight: '80%',
  },
  optionItem: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.two,
    borderRadius: Spacing.two,
  },
  agentRow: {
    borderRadius: Spacing.two,
    padding: Spacing.two,
    gap: Spacing.one,
  },
  agentInfo: {
    gap: Spacing.half,
  },
  editorSheet: {
    borderRadius: Spacing.three,
    overflow: 'hidden',
  },
  editorBody: {
    borderRadius: Spacing.three,
    padding: Spacing.four,
    gap: Spacing.two,
    maxHeight: '85%',
  },
  editorScroll: {
    gap: Spacing.two,
  },
  editorActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: Spacing.two,
  },
  loadingRow: {
    paddingVertical: Spacing.three,
    alignItems: 'center',
  },
  pressed: {
    opacity: 0.5,
  },
});
