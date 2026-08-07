'use client';

import { PluginCard } from './PluginCard';
import { Plugin } from '@/types';

interface PluginListProps {
  plugins: Plugin[];
  onEnable: (id: string) => Promise<void>;
  onDisable: (id: string) => Promise<void>;
  loading: boolean;
}

export function PluginList({ plugins, onEnable, onDisable, loading }: PluginListProps) {
  if (plugins.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No plugins available
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {plugins.map((plugin) => (
        <PluginCard
          key={plugin.id}
          plugin={plugin}
          onEnable={() => onEnable(plugin.id)}
          onDisable={() => onDisable(plugin.id)}
          loading={loading}
        />
      ))}
    </div>
  );
}