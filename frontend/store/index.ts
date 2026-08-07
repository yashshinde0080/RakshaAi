import { create } from 'zustand';
import type { SystemStatus, Hardware, Metrics, HistoryPoint } from '@/types';

interface Store {
  // System
  systemStatus: SystemStatus | null;
  setSystemStatus: (status: SystemStatus) => void;

  hardware: Hardware | null;
  setHardware: (hw: Hardware) => void;

  // New Universal Task State
  currentModel: string;
  taskType: string;
  executionMode: "fullram" | "layerstream" | "auto";
  inputSchema: Record<string, unknown>;
  isGenerative: boolean;

  setCurrentModel: (model: string) => void;
  setTaskType: (task: string) => void;
  setExecutionMode: (mode: "fullram" | "layerstream" | "auto") => void;
  setIsGenerative: (isGen: boolean) => void;

  // Metrics
  metrics: Metrics | null;
  setMetrics: (metrics: Metrics | null) => void;

  connected: boolean;
  setConnected: (connected: boolean) => void;

  history: HistoryPoint[];
  setHistory: (history: HistoryPoint[] | ((prev: HistoryPoint[]) => HistoryPoint[])) => void;

  // UI State
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
}


export const useStore = create<Store>((set) => ({
  systemStatus: null,
  setSystemStatus: (status) => set({ systemStatus: status }),

  hardware: null,
  setHardware: (hw) => set({ hardware: hw }),

  currentModel: "",
  taskType: "",
  executionMode: "auto",
  inputSchema: {},
  isGenerative: false,

  setCurrentModel: (model) => set({ currentModel: model }),
  setTaskType: (task) => set({ taskType: task }),
  setExecutionMode: (mode) => set({ executionMode: mode }),
  setIsGenerative: (isGen: boolean) => set({ isGenerative: isGen }),

  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  connected: false,
  setConnected: (connected) => set({ connected }),

  history: [],
  setHistory: (history) => set((state) => ({
    history: typeof history === 'function' ? history(state.history) : history
  })),

  settingsOpen: false,
  setSettingsOpen: (open) => set({ settingsOpen: open }),
}));
