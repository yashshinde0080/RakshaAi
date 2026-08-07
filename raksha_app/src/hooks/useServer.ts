import { useCallback, useEffect, useState } from 'react';

import { errMsg, getHardware, getSystemStatus, listModels, loadModel, unloadModel } from '@/api';
import type { HardwareProfile, Model, SystemStatus } from '@/types';

export function useServer() {
  const [models, setModels] = useState<Model[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, s, h] = await Promise.all([listModels(), getSystemStatus(), getHardware()]);
      setModels(m.models ?? []);
      setStatus(s);
      setHardware(h);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const load = useCallback(async (model: string) => {
    setBusyId(model);
    setError(null);
    try {
      await loadModel(model, 'auto');
      setStatus(await getSystemStatus());
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusyId(null);
    }
  }, []);

  const unload = useCallback(async () => {
    setBusyId('__unload__');
    setError(null);
    try {
      await unloadModel();
      setStatus(await getSystemStatus());
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusyId(null);
    }
  }, []);

  return { models, status, hardware, loading, busyId, error, refresh, load, unload };
}
