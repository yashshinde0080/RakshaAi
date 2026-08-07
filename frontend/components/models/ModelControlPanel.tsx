'use client';

import React from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useStore } from '@/store';
import { useModels } from '@/hooks/useModels';
import { 
  Zap, 
  Power, 
  Activity, 
  Layers, 
  MemoryStick, 
  ChevronRight,
  ShieldCheck,
  Microchip
} from 'lucide-react';
import { motion } from 'framer-motion';

export function ModelControlPanel() {
  const { systemStatus, currentModel, executionMode } = useStore();
  const { unloadModel, switchMode, loading } = useModels();

  const isLoaded = !!currentModel;
  const ramPercent = systemStatus ? (systemStatus.ram_used_gb / systemStatus.ram_total_gb) * 100 : 0;

  return (
    <Card className="relative overflow-hidden border-2 border-primary/20 bg-black/40 backdrop-blur-xl">
      {/* Decorative background pulse */}
      <div className="absolute top-0 right-0 -mr-20 -mt-20 h-64 w-64 rounded-full bg-primary/5 blur-[100px]" />
      <div className="absolute bottom-0 left-0 -ml-20 -mb-20 h-64 w-64 rounded-full bg-blue-500/5 blur-[100px]" />
      
      <CardContent className="p-0">
        <div className="grid grid-cols-1 lg:grid-cols-12">
          {/* Main Status Section */}
          <div className="lg:col-span-8 p-6 space-y-6">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full animate-pulse ${isLoaded ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,1)]' : 'bg-muted'}`} />
                  <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">System Core</span>
                </div>
                <h2 className="text-2xl font-black tracking-tight flex items-center gap-3">
                  {isLoaded ? currentModel : 'CORE IDLE'}
                  {isLoaded && <Badge className="bg-primary/10 text-primary border-primary/20">Active</Badge>}
                </h2>
              </div>
              
              {isLoaded && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="border-red-500/20 text-red-400 hover:bg-red-500/10 hover:text-red-500 transition-all font-mono text-xs uppercase tracking-tighter"
                  onClick={() => unloadModel()}
                  disabled={loading}
                >
                  <Power className="mr-2 h-3 w-3" />
                  Terminate Session
                </Button>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatItem 
                icon={<Layers className="h-4 w-4 text-blue-400" />} 
                label="Execution Mode" 
                value={executionMode?.toUpperCase() || 'AUTO'} 
              />
              <StatItem 
                icon={<MemoryStick className="h-4 w-4 text-purple-400" />} 
                label="RAM Allocation" 
                value={`${systemStatus?.ram_used_gb.toFixed(1) || 0} / ${systemStatus?.ram_total_gb.toFixed(0) || 0} GB`} 
              />
              <StatItem 
                icon={<Activity className="h-4 w-4 text-orange-400" />} 
                label="Latency" 
                value="< 15ms" 
              />
              <StatItem 
                icon={<ShieldCheck className="h-4 w-4 text-emerald-400" />} 
                label="Integrity" 
                value="Verified" 
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                <span>Power Distribution (RAM)</span>
                <span>{ramPercent.toFixed(1)}% Usage</span>
              </div>
              <div className="h-1.5 w-full bg-muted/20 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-primary shadow-[0_0_10px_theme(colors.primary.DEFAULT)]"
                  initial={{ width: 0 }}
                  animate={{ width: `${ramPercent}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
            </div>
          </div>

          {/* Quick Actions / Recommendations Sidebar */}
          <div className="lg:col-span-4 bg-primary/5 border-l border-primary/10 p-6 flex flex-col justify-between">
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                <Zap className="h-3 w-3" />
                Quick Commands
              </h3>
              
              <div className="space-y-2">
                <ActionButton label="Open Neural Console" href="/console" />
                <ActionButton label="View Hardware Topology" href="/system" />
                {executionMode === 'fullram' ? (
                  <ActionButton 
                    label="Switch to LayerStream" 
                    onClick={() => switchMode('layerstream')} 
                  />
                ) : (
                  <ActionButton 
                    label="Switch to Full RAM" 
                    onClick={() => switchMode('fullram')} 
                  />
                )}
              </div>
            </div>

            <div className="mt-8 p-4 rounded-lg bg-black/40 border border-primary/10 space-y-2">
              <div className="flex items-center gap-2 text-[10px] font-bold text-primary/60 uppercase tracking-tighter">
                <Microchip className="h-3 w-3" />
                Hardware Optimization
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Your <span className="text-foreground">AVX-512</span> unit is detected. Performance boost of 15% applied to transformer layers.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatItem({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        <span className="text-[10px] uppercase font-bold tracking-tight">{label}</span>
      </div>
      <div className="text-sm font-mono font-medium">{value}</div>
    </div>
  );
}

function ActionButton({ label, href, onClick }: { label: string, href?: string, onClick?: () => void }) {
  const content = (
    <div className="group flex items-center justify-between p-3 rounded-lg border border-primary/5 bg-white/5 hover:bg-primary/10 hover:border-primary/20 transition-all cursor-pointer">
      <span className="text-xs font-medium">{label}</span>
      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }


  return <div onClick={onClick}>{content}</div>;
}
