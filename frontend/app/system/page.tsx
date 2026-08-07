'use client';

import { useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { HardwareCard } from '@/components/system/HardwareCard';
import { MetricCard } from '@/components/system/MetricCard';
import { ResourceChart } from '@/components/system/ResourceChart';
import { useMetrics } from '@/hooks/useMetrics';
import { useStore } from '@/store';
import { Cpu, MemoryStick, HardDrive, Gpu, Activity } from 'lucide-react';
import { api } from '@/lib/api';


export default function SystemPage() {
  const { hardware, setHardware, systemStatus, setSystemStatus } = useStore();
  const { metrics, history, connected } = useMetrics();

  useEffect(() => {
    const fetchSystemData = async () => {
      console.log('Fetching system data...');
      try {
        const [hw, status] = await Promise.all([
          api.getHardware(),
          api.getSystemStatus()
        ]);
        console.log('Hardware:', hw);
        console.log('Status:', status);
        setHardware(hw);
        setSystemStatus(status);
      } catch (e) {
        console.error('Failed to fetch system data:', e);
      }
    };
    fetchSystemData();
  }, [setHardware, setSystemStatus]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">System</h1>
        <p className="text-muted-foreground">
          Hardware profile and resource monitoring
        </p>
      </div>

      {/* Hardware Profile */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <HardwareCard
          title="CPU"
          icon={Cpu}
          value={hardware?.cpu_name || 'Unknown'}
          details={[
            `${hardware?.cpu_cores || 0} cores / ${hardware?.cpu_threads || 0} threads`,
            `AVX2: ${hardware?.has_avx2 ? '✓' : '✗'} | AVX512: ${hardware?.has_avx512 ? '✓' : '✗'}`
          ]}
        />
        <HardwareCard
          title="Memory"
          icon={MemoryStick}
          value={`${hardware?.ram_total_gb?.toFixed(1) || 0} GB`}
          details={[
            `Available: ${systemStatus?.ram_available_gb?.toFixed(1) || 0} GB`,
            `Used: ${systemStatus?.ram_used_gb?.toFixed(1) || 0} GB`
          ]}
        />
        <HardwareCard
          title="Storage"
          icon={HardDrive}
          value={hardware?.disk_type || 'Unknown'}
          details={[
            `Speed: ${hardware?.disk_speed_mb_s?.toFixed(0) || 0} MB/s`,
            `Free: ${systemStatus?.disk_free_gb?.toFixed(0) || 0} GB`
          ]}
        />
        <HardwareCard
          title="GPU"
          icon={Gpu}
          value={hardware?.gpu_name || 'None'}
          details={[
            hardware?.gpu_vram_gb ? `VRAM: ${hardware.gpu_vram_gb} GB` : 'No GPU detected'
          ]}
        />
      </div>

      {/* Live Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          title="CPU Usage"
          value={metrics?.cpu_percent || 0}
          unit="%"
          status={(metrics?.cpu_percent ?? 0) > 80 ? 'critical' : (metrics?.cpu_percent ?? 0) > 50 ? 'warning' : 'normal'}
        />
        <MetricCard
          title="GPU Usage"
          value={metrics?.gpu_percent || 0}
          unit="%"
          status={(metrics?.gpu_percent ?? 0) > 80 ? 'critical' : (metrics?.gpu_percent ?? 0) > 50 ? 'warning' : 'normal'}
        />
        <MetricCard
          title="RAM Usage"
          value={metrics?.ram_percent || 0}
          unit="%"
          status={(metrics?.ram_percent ?? 0) > 80 ? 'critical' : (metrics?.ram_percent ?? 0) > 60 ? 'warning' : 'normal'}
        />
        <MetricCard
          title="Disk Read"
          value={metrics?.disk_read_mb || 0}
          unit="MB/s"
        />
        <MetricCard
          title="Disk Write"
          value={metrics?.disk_write_mb || 0}
          unit="MB/s"
        />
      </div>

      {/* Resource Charts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Resource History
          </CardTitle>
          <CardDescription>
            {connected ? 'Live updates' : 'Disconnected - Reconnecting...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResourceChart data={history} />
        </CardContent>
      </Card>

      {/* Engine Stats */}
      {systemStatus?.engine_stats && Object.keys(systemStatus.engine_stats).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Engine Statistics</CardTitle>
            <CardDescription>
              Current model: {systemStatus.current_model} ({systemStatus.current_mode})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(systemStatus.engine_stats).map(([key, value]) => (
                <div key={key} className="p-3 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">{key.replace(/_/g, ' ')}</p>
                  <p className="text-lg font-semibold">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}