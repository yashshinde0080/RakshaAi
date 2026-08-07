'use client';

import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useStore } from '@/store';
import { useMetrics } from '@/hooks/useMetrics';
import { Circle, Cpu, MemoryStick } from 'lucide-react';

export function TopBar() {
  const { systemStatus } = useStore();
  const { metrics, connected } = useMetrics();

  return (
    <header className="h-14 border-b bg-card px-6 flex items-center justify-between">
      {/* Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Circle
            className={`h-2 w-2 ${
              systemStatus?.model_loaded ? 'fill-green-500 text-green-500' : 'fill-muted text-muted'
            }`}
          />
          <span className="text-sm">
            {systemStatus?.model_loaded ? (
              <>
                <span className="font-medium">{systemStatus.current_model}</span>
                <span className="text-muted-foreground"> | {systemStatus.current_mode}</span>
              </>
            ) : (
              <span className="text-muted-foreground">No model loaded</span>
            )}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <Cpu className="h-4 w-4 text-muted-foreground" />
          <span className={(metrics?.cpu_percent ?? 0) > 80 ? 'text-red-500' : ''}>
            {metrics?.cpu_percent?.toFixed(0) || 0}%
          </span>
        </div>

        <Separator orientation="vertical" className="h-4" />

        <div className="flex items-center gap-2 text-sm">
          <MemoryStick className="h-4 w-4 text-muted-foreground" />
          <span className={(metrics?.ram_percent ?? 0) > 80 ? 'text-red-500' : ''}>
            {metrics?.ram_used_gb?.toFixed(1) || 0} GB
          </span>
        </div>

        <Separator orientation="vertical" className="h-4" />

        <Badge variant={connected ? 'default' : 'secondary'} className="text-xs">
          {connected ? 'Connected' : 'Offline'}
        </Badge>
      </div>
    </header>
  );
}