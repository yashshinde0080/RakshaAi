'use client';

import { useEffect, useRef } from 'react';
import { useStore } from '@/store';
import { metricsWs } from '@/lib/websocket';
import { api } from '@/lib/api';
import type { SystemStatus } from '@/types';

export function useMetrics() {
  const {
    metrics, setMetrics,
    systemStatus, setSystemStatus,
    setCurrentModel, setExecutionMode,
    setTaskType, setIsGenerative,
    connected, setConnected,
    history, setHistory
  } = useStore();
  const statusRef = useRef(systemStatus);

  // Keep ref up to date
  useEffect(() => {
    statusRef.current = systemStatus;
  }, [systemStatus]);

  useEffect(() => {
    // Initial system status sync
    const syncStatus = async () => {
      try {
        const status = await api.getSystemStatus();
        setSystemStatus(status);
        if (status.model_loaded) {
          setCurrentModel(status.current_model || "");
          setExecutionMode((status.current_mode as "fullram" | "layerstream" | "auto") || "auto");
          setTaskType(status.task_type || "");
          setIsGenerative(status.is_generative || false);
        }
      } catch (e) {
        console.error('Failed to sync system status:', e);
      }
    };

    syncStatus();

    metricsWs.connect();

    const unsubscribe = metricsWs.subscribe((data) => {
      setMetrics(data);
      setConnected(true);

      // Sync model state if it changed
      if (data.model_loaded !== undefined) {
        setCurrentModel(data.model_loaded || "");
        setExecutionMode((data.mode as "fullram" | "layerstream" | "auto") || "auto");
        setTaskType(data.task_type || "");
        setIsGenerative(data.is_generative || false);

        // Update top-level systemStatus model_loaded boolean if needed
        const currentStatus = statusRef.current;
        if (currentStatus && (
            currentStatus.current_model !== data.model_loaded ||
            currentStatus.current_mode !== data.mode ||
            currentStatus.task_type !== data.task_type
        )) {
           setSystemStatus({
             ...currentStatus,
             model_loaded: !!data.model_loaded,
             current_model: data.model_loaded,
             current_mode: data.mode,
             task_type: data.task_type,
             is_generative: !!data.is_generative
           });
        }
      }

      const now = new Date().toLocaleTimeString();
      setHistory((prev) => {
        const newHistory = [
          ...prev,
          {
            time: now,
            cpu: data.cpu_percent,
            gpu: data.gpu_percent,
            ram: data.ram_percent,
            diskRead: data.disk_read_mb,
            diskWrite: data.disk_write_mb
          },
        ];
        return newHistory.slice(-60);
      });
    });

    const interval = setInterval(() => {
      setConnected(metricsWs.isConnected());
    }, 1000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [setMetrics, setCurrentModel, setExecutionMode, setSystemStatus, setTaskType, setIsGenerative, setConnected, setHistory]);

  return { metrics, history, connected };
}
