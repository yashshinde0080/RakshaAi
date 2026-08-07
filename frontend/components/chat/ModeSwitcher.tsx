'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useStore } from '@/store';
import { api } from '@/lib/api';
import { ChevronDown, Cpu, Layers, Sparkles } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { errMsg } from '@/lib/utils';

const modes = [
  { id: 'fullram', label: 'Full RAM', icon: Cpu, description: 'Fastest, uses more memory' },
  { id: 'layerstream', label: 'Layer Stream', icon: Layers, description: 'Lower memory usage' },
  { id: 'auto', label: 'Auto', icon: Sparkles, description: 'Automatic selection' },
];

export function ModeSwitcher() {
  const { systemStatus, setSystemStatus } = useStore();
  const [switching, setSwitching] = useState(false);
  const { toast } = useToast();

  const currentMode = modes.find(m => m.id === systemStatus?.current_mode) || modes[2];

  const handleSwitch = async (mode: string) => {
    if (mode === systemStatus?.current_mode) return;

    setSwitching(true);
    try {
      const result = await api.switchMode(mode);
      setSystemStatus({
        ...systemStatus!,
        current_mode: result.mode
      });
      toast({
        title: 'Mode switched',
        description: `Now using ${mode} mode`,
      });
    } catch (error) {
      toast({
        title: 'Failed to switch mode',
        description: errMsg(error),
        variant: 'destructive',
      });
    } finally {
      setSwitching(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={switching}>
          <currentMode.icon className="h-4 w-4 mr-2" />
          {currentMode.label}
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {modes.map((mode) => (
          <DropdownMenuItem
            key={mode.id}
            onClick={() => handleSwitch(mode.id)}
            className="flex items-start gap-2"
          >
            <mode.icon className="h-4 w-4 mt-0.5" />
            <div>
              <p className="font-medium">{mode.label}</p>
              <p className="text-xs text-muted-foreground">{mode.description}</p>
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}