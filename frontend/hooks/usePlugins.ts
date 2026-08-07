'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import { errMsg } from '@/lib/utils';
import { Plugin } from '@/types';

export function usePlugins() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listPlugins();
      setPlugins(res || []);
    } catch (error) {
      toast({
        title: 'Failed to load plugins',
        description: errMsg(error),
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const enablePlugin = useCallback(async (pluginId: string) => {
    try {
      await api.enablePlugin(pluginId);
      await refresh();
      toast({
        title: 'Plugin enabled',
        description: `${pluginId} is now active`,
      });
    } catch (error) {
      toast({
        title: 'Failed to enable plugin',
        description: errMsg(error),
        variant: 'destructive',
      });
    }
  }, [refresh, toast]);

  const disablePlugin = useCallback(async (pluginId: string) => {
    try {
      await api.disablePlugin(pluginId);
      await refresh();
      toast({
        title: 'Plugin disabled',
        description: `${pluginId} is now inactive`,
      });
    } catch (error) {
      toast({
        title: 'Failed to disable plugin',
        description: errMsg(error),
        variant: 'destructive',
      });
    }
  }, [refresh, toast]);

  return {
    plugins,
    loading,
    refresh,
    enablePlugin,
    disablePlugin,
  };
}
