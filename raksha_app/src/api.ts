// src/api.ts
import axios from 'axios';
import Constants from 'expo-constants';

import type { HardwareProfile, Message, Model, RagSource, SystemStatus } from '@/types';

// API URL resolution order: EXPO_PUBLIC_API_URL env var → the dev-server host
// that serves the bundle (a phone on the same Wi-Fi reaches the laptop's LAN
// IP automatically) → localhost.
// ponytail: hostUri exists only in dev; production builds must set
// EXPO_PUBLIC_API_URL (a phone can't reach "localhost" of the server).
function resolveApiUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) return envUrl;
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

export async function getSystemStatus(): Promise<SystemStatus> {
  const { data } = await api.get('/system/status');
  return data;
}

export async function getHardware(): Promise<HardwareProfile> {
  const { data } = await api.get('/system/hardware');
  return data;
}

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
