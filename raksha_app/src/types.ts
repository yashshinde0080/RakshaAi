export interface RagSource {
  filename: string;
  document_id?: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  /** Model's internal reasoning (e.g. Qwen3.5 <think> blocks), shown collapsible. */
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
  downloaded: boolean;
  modes_supported: string[];
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
}

export interface HardwareProfile {
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
