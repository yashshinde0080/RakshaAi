'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import type { TaskResult } from '@/types';
import { Loader2, Fingerprint } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

export function EmbeddingModule() {
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
    <div className="p-6 h-full flex flex-col items-center justify-start max-w-4xl mx-auto w-full gap-6">
         <h2 className="text-xl font-bold w-full text-left">Text Encoding & Embeddings</h2>
        
         <Card className="w-full">
            <CardContent className="p-4 flex flex-col gap-4">
                <Textarea 
                    placeholder="Enter text to convert to vector embedding..." 
                    value={input} 
                    onChange={e => setInput(e.target.value)}
                    className="min-h-[120px]"
                />
                <Button onClick={handleRun} disabled={loading || !input.trim()} className="self-end w-32 shadow-sm">
                    {loading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Fingerprint className="h-4 w-4 mr-2" />}
                    Encode
                </Button>
            </CardContent>
        </Card>

        {result && (
            <Card className="w-full">
               <CardContent className="p-6 bg-gradient-to-r from-primary/5 pb-2">
                    <span className="text-sm font-medium text-muted-foreground mb-2 block">Tensor Emission Shape</span>
                    <p className="font-mono text-sm bg-background p-2 rounded border border-border">
                        {JSON.stringify(result.shape || "[Hidden States Emitted]")}
                    </p>
               </CardContent>
            </Card>
        )}
    </div>
  );
}
