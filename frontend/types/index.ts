import type { MaskPrediction } from '@/lib/maskedLm';

export interface RagSource {
  /** Display name of the cited document. */
  filename: string;
  /** Vector-store document id, used to fetch chunk previews. Absent on legacy messages. */
  document_id?: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  /** Model's internal reasoning (e.g. Qwen3.5 <think> blocks), shown in a collapsible block. */
  reasoning?: string;
  /** RAG sources cited by an assistant reply (from stream rag_metadata). */
  sources?: RagSource[];
}

export interface Model {
  id: string;
  name: string;
  size_gb: number;
  quant: string;
  family: string;
  parameters: string;
  path: string;
  downloaded: boolean;
  modes_supported: string[];
  created_at?: string;
}

export interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  enabled: boolean;
  builtin: boolean;
  actions: string[];
}

export interface SystemStatus {
  model_loaded: boolean;
  current_model: string | null;
  current_mode: string | null;
  task_type: string | null;
  is_generative: boolean;
  ram_total_gb: number;
  ram_used_gb: number;
  ram_available_gb: number;
  disk_total_gb: number;
  disk_used_gb: number;
  disk_free_gb: number;
  engine_stats: Record<string, unknown>;
}

export interface Hardware {
  cpu_name: string;
  cpu_cores: number;
  cpu_threads: number;
  has_avx2: boolean;
  has_avx512: boolean;
  ram_total_gb: number;
  gpu_name: string | null;
  gpu_vram_gb: number | null;
  disk_type: string;
  disk_speed_mb_s: number;
}

export interface Metrics {
  cpu_percent: number;
  gpu_percent: number;
  gpu_vram_used: number;
  ram_percent: number;
  ram_used_gb: number;
  disk_read_mb: number;
  disk_write_mb: number;
  model_loaded: string | null;
  mode: string | null;
  task_type: string | null;
  is_generative: boolean;
  engine_stats: Record<string, unknown>;
}

export interface HistoryPoint {
  time: string;
  cpu: number;
  gpu?: number;
  ram: number;
  diskRead?: number;
  diskWrite?: number;
}

export interface BenchmarkResult {
  model: string;
  mode: string;
  iterations: number;
  runs: BenchmarkRun[];
  summary: BenchmarkSummary;
}

export interface BenchmarkRun {
  iteration: number;
  tokens: number;
  time_seconds: number;
  tokens_per_second: number;
}

export interface BenchmarkSummary {
  total_tokens: number;
  total_time_seconds: number;
  average_tokens_per_second: number;
  peak_ram_gb: number;
}

export interface Document {
  id: string;
  filename: string;
  chunks: number;
  created_at: string;
}

export interface QueryResult {
  query: string;
  results: SearchResult[];
  generated_response: string | null;
}

export interface SearchResult {
  text: string;
  score: number;
  metadata: Record<string, unknown>;
  document_id: string;
}

export interface Recommendation {
  model: string;
  mode: string;
  confidence: string;
}

export interface CurrentModel {
  loaded: boolean;
  model: string;
  task_type: string;
  mode: string;
  is_generative: boolean;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  description: string;
  system_instruction: string;
  is_active: boolean;
  icon: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
}

export interface WorkspaceSnapshot {
  id: string;
  model: string | null;
  mode: string | null;
  timestamp: number;
  created: string;
}

export interface TaskResult {
  output?: string;
  confidence?: string;
  shape?: unknown;
  metadata?: Record<string, unknown>;
  predictions?: MaskPrediction[];
  message?: string;
}

export interface DownloadStatus {
  status?: string;
  progress?: number;
  downloaded_gb?: number;
  total_gb?: number;
  error?: string;
}

export interface SettingsMap {
  agents?: Agent[];
  general?: Record<string, unknown>;
  project?: Record<string, unknown>;
  personalization?: Record<string, unknown>;
  data_controls?: Record<string, unknown>;
  security?: Record<string, unknown>;
  parental_controls?: Record<string, unknown>;
  [key: string]: unknown;
}
