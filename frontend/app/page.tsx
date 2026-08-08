'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useStore } from '@/store';
import { api } from '@/lib/api';
import { BrandMark } from '@/components/BrandMark';
import { Cpu, HardDrive, ArrowRight, Gauge, Sparkles, Rocket, HeartPulse } from 'lucide-react';
import Link from 'next/link';
import { ModelControlPanel } from '@/components/models/ModelControlPanel';
import type { Recommendation } from '@/types';

export default function HomePage() {
  const { systemStatus, setSystemStatus, hardware, setHardware } = useStore();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, hwRes, recRes] = await Promise.all([
          api.getSystemStatus(),
          api.getHardware(),
          api.getRecommendations()
        ]);
        
        setSystemStatus(statusRes);
        setHardware(hwRes);
        setRecommendations(recRes.recommendations || []);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const noModelLoaded = !systemStatus?.model_loaded;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <BrandMark size={48} />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome to Raksha AI</h1>
          <p className="text-muted-foreground mt-1">
            Your private, offline AI guardian — local intelligence and vitals triage, zero cloud.
          </p>
        </div>
      </div>

      {/* First-run hardware suggestions banner */}
      {noModelLoaded && recommendations.length > 0 && (
        <Card className="border-primary/30 bg-gradient-to-r from-primary/5 to-primary/10 overflow-hidden relative">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 h-32 w-32 rounded-full bg-primary/10 blur-[80px]" />
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="h-5 w-5 text-primary" />
              <span className="text-xs font-bold uppercase tracking-widest text-primary">Hardware Optimized</span>
            </div>
            <h2 className="text-lg font-bold mb-1">Models Recommended for Your System</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Based on {hardware?.cpu_name || 'your hardware'} with {hardware?.ram_total_gb}GB RAM
            </p>
            <div className="flex flex-wrap gap-2 mb-4">
              {recommendations.slice(0, 4).map((rec, i) => (
                <Badge key={i} variant="outline" className="px-3 py-1 text-xs flex items-center gap-1">
                  <Rocket className="h-3 w-3" />
                  {rec.model}
                  <span className="text-muted-foreground ml-1">({rec.mode})</span>
                </Badge>
              ))}
            </div>
            <Link href="/models">
              <Button size="sm">
                Browse Models
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Core Control Panel */}
      <ModelControlPanel />

      {/* Hardware Details & Storage */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-muted/30 border-none">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Processor</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{hardware?.cpu_name || 'Generic CPU'}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {hardware?.cpu_cores} Physical Cores | {hardware?.cpu_threads} Threads
            </p>
          </CardContent>
        </Card>

        <Card className="bg-muted/30 border-none">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Neural Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{systemStatus?.disk_free_gb?.toFixed(0) || 0} GB Free</div>
            <p className="text-xs text-muted-foreground mt-1">
              Type: {hardware?.disk_type} | Velocity: {hardware?.disk_speed_mb_s?.toFixed(0)} MB/s
            </p>
          </CardContent>
        </Card>

        <Card className="bg-muted/30 border-none">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">System Health</CardTitle>
            <Gauge className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">Optimal</div>
            <p className="text-xs text-muted-foreground mt-1">
              All neural pathways are functioning correctly.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-brand/40 bg-brand/5 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 h-24 w-24 rounded-full bg-brand/10 blur-2xl" />
          <CardHeader>
            <div className="flex items-center gap-2">
              <HeartPulse className="h-5 w-5 text-brand" />
              <CardTitle className="text-base">Medical Triage</CardTitle>
            </div>
            <CardDescription>
              ESI triage with two AI safety gates — runs even without a model
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/triage">
              <Button className="w-full bg-brand hover:bg-brand/90 text-white">
                Run Triage
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Get Started</CardTitle>
            <CardDescription>
              Start executing AI locally
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {systemStatus?.model_loaded ? (
              <Link href="/console">
                <Button className="w-full">
                  Open Console
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            ) : (
              <Link href="/models">
                <Button className="w-full">
                  Load a Model
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recommended Models</CardTitle>
            <CardDescription>
              Based on your hardware
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recommendations.slice(0, 3).map((rec, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                >
                  <div>
                    <span className="font-medium">{rec.model}</span>
                    <Badge variant="outline" className="ml-2">
                      {rec.mode}
                    </Badge>
                  </div>
                  <Badge
                    variant={rec.confidence === 'high' ? 'default' : 'secondary'}
                  >
                    {rec.confidence}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
