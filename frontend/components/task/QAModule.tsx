'use client';

import { useState } from 'react';
import { Card, CardContent, CardTitle, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import type { TaskResult } from '@/types';
import { Loader2 } from 'lucide-react';

export function QAModule() {
  const [context, setContext] = useState('');
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    if (!context.trim() || !question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.executeTask({ context, question });
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 h-full flex flex-col items-center justify-start max-w-4xl mx-auto w-full gap-6">
        <h2 className="text-xl font-bold w-full text-left">Extractive Question Answering</h2>
        
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-sm font-medium">Article / Context</CardTitle>
            </CardHeader>
            <CardContent>
                <Textarea 
                    placeholder="Paste the reference context here..." 
                    value={context} 
                    onChange={e => setContext(e.target.value)}
                    className="min-h-[160px] resize-y"
                />
            </CardContent>
        </Card>

        <Card className="w-full">
             <CardHeader>
                <CardTitle className="text-sm font-medium">Question</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
                <Input 
                    placeholder="What would you like to know?" 
                    value={question} 
                    onChange={e => setQuestion(e.target.value)}
                />
                
                <Button onClick={handleRun} disabled={loading || !context.trim() || !question.trim()} className="self-end w-32">
                    {loading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : null}
                    Extract
                </Button>
            </CardContent>
        </Card>

        {result && (
            <Card className="w-full bg-primary/10 border-primary/20">
                <CardContent className="p-6">
                    <span className="text-sm font-medium text-muted-foreground mb-2 block">Extracted Answer</span>
                    <p className="text-lg font-semibold">{result.output}</p>
                </CardContent>
            </Card>
        )}
    </div>
  );
}
