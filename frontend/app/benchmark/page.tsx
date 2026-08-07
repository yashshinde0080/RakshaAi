'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useStore } from '@/store';
import { api } from '@/lib/api';
import { Play, AlertCircle, GitCompare } from 'lucide-react';
import Link from 'next/link';

interface BenchmarkResult {
  model: string;
  mode: string;
  iterations: number;
  runs: Array<{
    iteration: number;
    tokens: number;
    time_seconds: number;
    tokens_per_second: number;
  }>;
  summary: {
    total_tokens: number;
    total_time_seconds: number;
    average_tokens_per_second: number;
    peak_ram_gb: number;
  };
}

interface ModeResult {
  tokens: number;
  time_s: number;
  tps: number;
  ram_gb: number;
}

interface CompareResponse {
  model: string;
  current_mode: string;
  results: Record<string, ModeResult | { available: false; reason: string }>;
}

const errMsg = (e: unknown): string => (e instanceof Error ? e.message : String(e));

export default function BenchmarkPage() {
  const { systemStatus } = useStore();
  const [iterations, setIterations] = useState(3);
  const [maxTokens, setMaxTokens] = useState(100);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);

  const runBenchmark = async () => {
    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const res = (await api.runBenchmark(iterations, maxTokens)) as BenchmarkResult;
      setResult(res);
    } catch (err) {
      setError(errMsg(err) || 'Benchmark failed');
    } finally {
      setRunning(false);
    }
  };

  if (!systemStatus?.model_loaded) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="p-6 max-w-md">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No model is loaded. Please load a model first to run benchmarks.
            </AlertDescription>
          </Alert>
          <Link href="/models" className="mt-4 block">
            <Button className="w-full">Go to Models</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Benchmark</h1>
        <p className="text-muted-foreground">
          Test inference performance
        </p>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>
            Model: {systemStatus.current_model} | Mode: {systemStatus.current_mode}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="iterations">Iterations</Label>
              <Input
                id="iterations"
                type="number"
                min={1}
                max={10}
                value={iterations}
                onChange={(e) => setIterations(parseInt(e.target.value) || 1)}
                disabled={running}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxTokens">Max Tokens</Label>
              <Input
                id="maxTokens"
                type="number"
                min={10}
                max={500}
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value) || 100)}
                disabled={running}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={runBenchmark} disabled={running} className="w-full">
                {running ? (
                  <>
                    <div
                      className="animate-spin rounded-full h-4 w-4 border-2 border-primary-foreground border-t-transparent mr-2"
                      aria-hidden="true"
                    ></div>
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Benchmark
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mode Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Mode Comparison
          </CardTitle>
          <CardDescription>
            Compare FullRAM vs LayerStream performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={async () => {
              setComparing(true);
              try {
                const res = await api.compareModes() as CompareResponse;
                setCompareResult(res);
              } catch (err) {
                setError(errMsg(err) || 'Comparison failed');
              }
              setComparing(false);
            }}
            disabled={comparing}
            variant="outline"
          >
            {comparing ? 'Comparing...' : 'Run Comparison'}
          </Button>

          {compareResult && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(compareResult.results || {}).map(([mode, data]) => (
                <div key={mode} className="p-4 rounded-lg border bg-card">
                  <h3 className="text-sm font-bold uppercase tracking-wider mb-2">{mode}</h3>
                  {'available' in data ? (
                    <p className="text-xs text-muted-foreground">{data.reason}</p>
                  ) : (
                    <div className="space-y-1 text-sm">
                      <p>TPS: <span className="font-mono font-bold text-success">{data.tps.toFixed(2)}</span></p>
                      <p>Time: <span className="font-mono">{data.time_s.toFixed(2)}s</span></p>
                      <p>Tokens: <span className="font-mono">{data.tokens}</span></p>
                      <p>RAM: <span className="font-mono">{data.ram_gb.toFixed(2)} GB</span></p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {result && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Results</CardTitle>
              <CardDescription>
                {result.iterations} iterations completed
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Iteration</TableHead>
                    <TableHead className="text-right">Tokens</TableHead>
                    <TableHead className="text-right">Time (s)</TableHead>
                    <TableHead className="text-right">TPS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.runs.map((run) => (
                    <TableRow key={run.iteration}>
                      <TableCell>{run.iteration}</TableCell>
                      <TableCell className="text-right">{run.tokens}</TableCell>
                      <TableCell className="text-right">{run.time_seconds.toFixed(3)}</TableCell>
                      <TableCell className="text-right font-medium text-success">
                        {run.tokens_per_second.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Total Tokens</p>
                  <p className="text-2xl font-bold">{result.summary.total_tokens}</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Total Time</p>
                  <p className="text-2xl font-bold">{result.summary.total_time_seconds.toFixed(2)}s</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Avg TPS</p>
                  <p className="text-2xl font-bold text-success">
                    {result.summary.average_tokens_per_second.toFixed(2)}
                  </p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Peak RAM</p>
                  <p className="text-2xl font-bold">{result.summary.peak_ram_gb.toFixed(2)} GB</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
