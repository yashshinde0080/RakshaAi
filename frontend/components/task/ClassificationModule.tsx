'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import type { TaskResult } from '@/types';
import { Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

export function ClassificationModule({ taskType }: { taskType: string }) {
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

  return (
    <div className="p-6 h-full flex flex-col items-center justify-center max-w-2xl mx-auto w-full">
        <h2 className="text-xl font-bold mb-6 w-full text-left">Sequence Classification</h2>
        <Card className="w-full">
            <CardContent className="p-4 flex flex-col gap-4">
                <Textarea 
                    placeholder="Enter text to classify..." 
                    value={input} 
                    onChange={e => setInput(e.target.value)}
                    className="min-h-[120px]"
                />
                <Button onClick={handleRun} disabled={loading || !input.trim()} className="self-end">
                    {loading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : null}
                    Classify
                </Button>
            </CardContent>
        </Card>

        {result && (
            <Card className="w-full mt-6 bg-primary/5 border-primary/20">
                <CardContent className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-sm text-muted-foreground">Predicted Label</span>
                        <Badge variant="default" className="text-lg px-3 py-1">{result.output}</Badge>
                    </div>
                    <div>
                        <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium">Confidence Score</span>
                            <span>{(parseFloat(result.confidence ?? "0") * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={parseFloat(result.confidence ?? "0") * 100} className="h-2" />
                    </div>
                </CardContent>
            </Card>
        )}
    </div>
  );
}
