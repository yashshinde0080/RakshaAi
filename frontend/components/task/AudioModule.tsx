'use client';

import { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import type { TaskResult } from '@/types';
import { Loader2, Music, Mic } from 'lucide-react';

export function AudioModule({ taskType }: { taskType: string }) {
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [audioBase64, setAudioBase64] = useState<string>('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
       setFilePreview(file.name);
       const reader = new FileReader();
       reader.onloadend = () => {
           setAudioBase64((reader.result as string).split(',')[1]);
       };
       reader.readAsDataURL(file);
    }
  };

  const handleRun = async () => {
    if (!audioBase64) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.executeTask({ audio: audioBase64 });
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 h-full flex flex-col items-center justify-start max-w-3xl mx-auto w-full gap-6">
        <h2 className="text-xl font-bold w-full text-left">{taskType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</h2>
        
        <Card className="w-full">
            <CardContent className="flex flex-col items-center justify-center p-12 hover:bg-muted/50 transition-colors border-dashed border-2 cursor-pointer" onClick={() => fileInputRef.current?.click()}>
               <Mic className="h-10 w-10 text-muted-foreground mb-4" />
               <span className="font-medium text-lg text-foreground mt-2">Upload Audio Trace</span>
               <span className="text-sm text-muted-foreground">WAV, MP3, FLAC</span>
               {filePreview && (
                   <div className="mt-4 flex items-center gap-2 p-2 bg-primary/10 rounded-md text-primary font-medium w-full justify-center">
                       <Music className="h-4 w-4" /> {filePreview}
                   </div>
               )}
               <input type="file" className="hidden" accept="audio/*" ref={fileInputRef} onChange={handleAudioChange} />
            </CardContent>
        </Card>

        {filePreview && (
             <Button onClick={handleRun} disabled={loading} size="lg" className="w-full max-w-xs">
                 {loading && <Loader2 className="animate-spin h-5 w-5 mr-2" />}
                 Process Audio
             </Button>
        )}

        {result && (
            <Card className="w-full bg-primary/5 border-primary/20">
                <CardContent className="p-6">
                    <span className="text-sm font-medium text-muted-foreground mb-2 block">Detection Result</span>
                    <p className="text-lg font-bold">{result.output}</p>
                </CardContent>
            </Card>
        )}
    </div>
  );
}
