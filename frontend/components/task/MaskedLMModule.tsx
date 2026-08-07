'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { buildSegments } from '@/lib/maskedLm';
import type { TaskResult } from '@/types';
import { Loader2, Sparkles, Wand2 } from 'lucide-react';

export function MaskedLMModule() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.executeTask({ prompt: input });
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const insertMask = () => {
    const mask = '[MASK]';
    setInput((prev) => {
      if (!prev) return mask;
      return prev.endsWith(' ') ? prev + mask : `${prev} ${mask}`;
    });
  };

  const message = result?.message ?? '';
  const predictions = result?.predictions ?? [];
  const isPlainMessage = result && message.trim() !== '' && predictions.length === 0;

  return (
    <div className="p-6 h-full flex flex-col items-center justify-start max-w-4xl mx-auto w-full gap-6 overflow-y-auto">
      <h2 className="text-xl font-bold w-full text-left">Masked Language Modeling</h2>

      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary" />
            Fill the [MASK]
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Textarea
            placeholder="The patient was diagnosed with [MASK] cancer."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="min-h-[120px] resize-y"
          />
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={insertMask}
              className="text-muted-foreground hover:text-foreground"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Insert [MASK]
            </Button>
            <Button
              onClick={handleRun}
              disabled={loading || !input.trim()}
              className="w-32 shadow-sm"
            >
              {loading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : null}
              Predict
            </Button>
          </div>
        </CardContent>
      </Card>

      {isPlainMessage && (
        <Card className="w-full bg-primary/5 border-primary/20">
          <CardContent className="p-6">
            <span className="text-sm font-medium text-muted-foreground mb-2 block">
              Model Response
            </span>
            <p className="text-base">{message}</p>
          </CardContent>
        </Card>
      )}

      {predictions.length > 0 && (
        <Card className="w-full bg-primary/5 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Fill-in-the-blank preview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base leading-relaxed">
              {buildSegments(input, predictions).map((seg, i) =>
                seg.filled ? (
                  <span
                    key={i}
                    className="bg-primary/20 text-primary font-semibold rounded px-1.5 py-0.5 mx-0.5"
                  >
                    {seg.text}
                  </span>
                ) : (
                  <span key={i}>{seg.text}</span>
                )
              )}
            </p>
          </CardContent>
        </Card>
      )}

      {predictions.map((pred) => (
        <Card key={pred.position} className="w-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">
              Mask Position{' '}
              <Badge variant="secondary" className="font-mono ml-1">
                {pred.position}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {pred.candidates.map((candidate, idx) => (
              <div key={candidate.token} className="flex items-center gap-3">
                <span
                  className={`w-40 truncate font-mono text-sm text-right ${
                    idx === 0 ? 'text-primary font-semibold' : 'text-muted-foreground'
                  }`}
                >
                  {candidate.token}
                </span>
                <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      idx === 0
                        ? 'bg-primary'
                        : 'bg-primary/40'
                    }`}
                    style={{ width: `${Math.min(candidate.probability * 100, 100)}%` }}
                  />
                </div>
                <span className="w-14 text-right text-sm tabular-nums text-muted-foreground">
                  {(candidate.probability * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      {result && predictions.length > 0 && (
        <p className="text-xs text-muted-foreground w-full text-right">
          Latency: {String(result.metadata?.latency ?? '—')} · RAM:{' '}
          {String(result.metadata?.ram_usage ?? '—')}
        </p>
      )}
    </div>
  );
}
