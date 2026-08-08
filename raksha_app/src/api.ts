// src/api.ts
import axios from 'axios';
import Constants from 'expo-constants';

import type {
  Agent,
  BenchmarkResult,
  CompareResponse,
  CurrentModel,
  DocInfo,
  HardwareProfile,
  Message,
  Model,
  Plugin,
  QueryResult,
  Recommendation,
  RagSource,
  ResourceUsage,
  SettingsMap,
  SystemStatus,
  TaskResult,
  TriageInput,
  TriageResult,
  WorkspaceSnapshot,
} from '@/types';

// API URL resolution order: EXPO_PUBLIC_API_URL env var → the dev-server host
// that serves the bundle (a phone on the same Wi-Fi reaches the laptop's LAN
// IP automatically) → localhost.
// ponytail: hostUri exists only in dev; production builds must set
// EXPO_PUBLIC_API_URL (a phone can't reach "localhost" of the server).
function resolveApiUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) return envUrl;
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return `http://${window.location.hostname}:8000`;
  }
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return `http://${host || 'localhost'}:8000`;
}

const api = axios.create({
  baseURL: `${resolveApiUrl()}/v1`,
  timeout: 15000,
});

export function errMsg(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  if (detail) return detail;
  return e instanceof Error ? e.message : String(e);
}

// ── Models ──────────────────────────────────────────────────────────────────
export async function listModels(): Promise<{ models: Model[] }> {
  const { data } = await api.get('/models/');
  return data;
}

export async function loadModel(model: string, mode = 'auto'): Promise<unknown> {
  const { data } = await api.post('/models/load', { model, mode });
  return data;
}

export async function unloadModel(): Promise<unknown> {
  const { data } = await api.post('/models/unload');
  return data;
}

export async function getCurrentModel(): Promise<CurrentModel> {
  const { data } = await api.get('/models/current');
  return data;
}

export async function getRecommendations(): Promise<Recommendation[]> {
  const { data } = await api.get('/system/recommendation');
  return data.recommendations ?? [];
}

// ── System ──────────────────────────────────────────────────────────────────
export async function getSystemStatus(): Promise<SystemStatus> {
  const { data } = await api.get('/system/status');
  return data;
}

export async function getHardware(): Promise<HardwareProfile> {
  const { data } = await api.get('/system/hardware');
  return data;
}

export async function getResources(): Promise<ResourceUsage> {
  const { data } = await api.get('/system/resources');
  return data;
}

// ── Chat / Tasks ────────────────────────────────────────────────────────────
export interface ChatDelta {
  content?: string;
  reasoning?: string;
  sources?: RagSource[];
  error?: string;
  done?: boolean;
}

/**
 * SSE chat stream over XHR. React Native's fetch cannot read streaming
 * response bodies; XHR's incremental readyState/responseText works on
 * iOS, Android and web with zero extra dependencies.
 */
export function streamChat(
  messages: Message[],
  enableThinking: boolean,
  onDelta: (d: ChatDelta) => void
): () => void {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${api.defaults.baseURL}/chat/completions`);
  xhr.setRequestHeader('Content-Type', 'application/json');
  let cursor = 0;
  let buffer = '';

  const flush = () => {
    const text = xhr.responseText;
    buffer += text.slice(cursor);
    cursor = text.length;
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame.split('\n').find((l) => l.startsWith('data: '));
      if (!dataLine) continue;
      const data = dataLine.slice(6).trim();
      if (data === '[DONE]') continue;
      try {
        const chunk = JSON.parse(data);
        const delta = chunk.choices?.[0]?.delta ?? {};
        if (delta.content || delta.reasoning || delta.rag_metadata) {
          onDelta({
            content: delta.content || '',
            reasoning: delta.reasoning || '',
            sources: delta.rag_metadata,
          });
        }
        if (chunk.choices?.[0]?.finish_reason) onDelta({ done: true });
      } catch {
        // Partial frame split across chunks — parsing continues next event.
      }
    }
  };

  xhr.onreadystatechange = () => {
    if (xhr.readyState === 3 || xhr.readyState === 4) flush();
    if (xhr.readyState === 4 && xhr.status !== 0) {
      if (xhr.status >= 200 && xhr.status < 300) {
        onDelta({ done: true });
      } else {
        let detail = `Chat request failed (${xhr.status})`;
        try {
          const j = JSON.parse(xhr.responseText);
          if (j.detail) detail = j.detail;
        } catch {
          // keep fallback message
        }
        onDelta({ error: detail });
      }
    }
  };
  xhr.onerror = () => onDelta({ error: 'Network error — is the backend reachable?' });
  xhr.send(
    JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: true,
      use_rag: true,
      // Thinking models burn tokens reasoning before the answer; the backend's
      // 512 default truncates mid-think, so give thinking a headroom budget.
      max_tokens: enableThinking ? 1024 : 512,
      enable_thinking: enableThinking,
    })
  );
  return () => xhr.abort();
}

export async function executeTask(data: Record<string, unknown>): Promise<TaskResult> {
  const { data: res } = await api.post('/chat/execute', data);
  return res;
}

// ── Documents / RAG ─────────────────────────────────────────────────────────
export async function listDocuments(): Promise<{ documents: DocInfo[] }> {
  const { data } = await api.get('/rag/documents');
  return data;
}

/** Pick a document with the system file picker and upload it (RN multipart). */
export async function uploadDocument(file: {
  uri: string;
  name: string;
  type: string;
}): Promise<unknown> {
  const form = new FormData();
  form.append('file', file as unknown as Blob);
  const { data } = await api.post('/rag/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return data;
}

export async function queryDocuments(query: string, topK = 5): Promise<QueryResult> {
  const { data } = await api.post('/rag/query', {
    query,
    top_k: topK,
    generate_response: true,
  });
  return data;
}

export async function deleteDocument(docId: string): Promise<unknown> {
  const { data } = await api.delete(`/rag/documents/${docId}`);
  return data;
}

// ── Plugins ─────────────────────────────────────────────────────────────────
export async function listPlugins(): Promise<Plugin[]> {
  const { data } = await api.get('/plugins/');
  return data;
}

export async function enablePlugin(pluginId: string): Promise<unknown> {
  const { data } = await api.post(`/plugins/${pluginId}/enable`);
  return data;
}

export async function disablePlugin(pluginId: string): Promise<unknown> {
  const { data } = await api.post(`/plugins/${pluginId}/disable`);
  return data;
}

// ── Benchmark ───────────────────────────────────────────────────────────────
export async function runBenchmark(
  iterations: number,
  maxTokens: number
): Promise<BenchmarkResult> {
  const { data } = await api.post('/benchmark/run', { iterations, max_tokens: maxTokens });
  return data;
}

export async function compareModes(): Promise<CompareResponse> {
  const { data } = await api.get('/benchmark/compare');
  return data;
}

// ── Workspace ───────────────────────────────────────────────────────────────
export async function saveWorkspace(): Promise<unknown> {
  const { data } = await api.post('/workspace/save');
  return data;
}

export async function listWorkspaces(): Promise<{ snapshots: WorkspaceSnapshot[] }> {
  const { data } = await api.get('/workspace/');
  return data;
}

export async function loadWorkspace(snapId: string): Promise<WorkspaceSnapshot> {
  const { data } = await api.get(`/workspace/${snapId}`);
  return data;
}

export async function deleteWorkspace(snapId: string): Promise<unknown> {
  const { data } = await api.delete(`/workspace/${snapId}`);
  return data;
}

// ── Settings ────────────────────────────────────────────────────────────────
export async function getAllSettings(): Promise<SettingsMap> {
  const { data } = await api.get('/settings');
  return data;
}

/** section is the settings key (e.g. 'general', 'data_controls'). */
export async function updateSettingsSection(
  section: string,
  sectionData: Record<string, unknown>
): Promise<unknown> {
  const { data } = await api.put(`/settings/${section.replace(/_/g, '-')}`, sectionData);
  return data;
}

export async function listAgents(): Promise<Agent[]> {
  const { data } = await api.get('/settings/agents');
  return data;
}

export async function createAgent(agent: Agent): Promise<unknown> {
  const { data } = await api.post('/settings/agents', agent);
  return data;
}

export async function updateAgent(agentId: string, agent: Agent): Promise<unknown> {
  const { data } = await api.put(`/settings/agents/${agentId}`, agent);
  return data;
}

export async function deleteAgent(agentId: string): Promise<unknown> {
  const { data } = await api.delete(`/settings/agents/${agentId}`);
  return data;
}

export async function activateAgent(agentId: string): Promise<unknown> {
  const { data } = await api.post(`/settings/agents/${agentId}/activate`);
  return data;
}

export async function deactivateAllAgents(): Promise<unknown> {
  const { data } = await api.post('/settings/agents/deactivate');
  return data;
}

export async function setSecurityPassword(password: string): Promise<unknown> {
  const { data } = await api.post('/settings/security/set-password', null, {
    params: { password },
  });
  return data;
}

export async function setParentalPin(pin: string): Promise<unknown> {
  const { data } = await api.post('/settings/parental-controls/set-pin', null, {
    params: { pin },
  });
  return data;
}

// ── Triage ──────────────────────────────────────────────────────────────────
export async function runTriage(input: TriageInput): Promise<TriageResult> {
  const { data } = await api.post('/triage/', input);
  return data;
}
