'use client';

import { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import type { TaskResult } from '@/types';
import { Loader2, UploadCloud, ImageIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export function VisionModule({ taskType }: { taskType: string }) {
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string>('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
       const reader = new FileReader();
       reader.onloadend = () => {
           setImagePreview(reader.result as string);
           setImageBase64((reader.result as string).split(',')[1]); // get base64 portion
       };
       reader.readAsDataURL(file);
    }
  };

  const handleRun = async () => {
    if (!imageBase64) return;
    setLoading(true);
    setResult(null);
    try {
      // Backend should be able to accept base64 or file upload, 
      // Assuming frontend sends a base64 encoded string `image`
      const res = await api.executeTask({ image: imageBase64 });
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
        
        <Card className="w-full flex border-dashed border-2 hover:bg-muted/50 transition-colors">
            <CardContent className="w-full flex flex-col items-center justify-center p-10 cursor-pointer text-muted-foreground" onClick={() => fileInputRef.current?.click()}>
                {imagePreview ? (
                    <img src={imagePreview} alt="Preview" className="max-h-64 object-contain rounded-md shadow-sm" />
                ) : (
                    <>
                       <UploadCloud className="h-10 w-10 mb-4" />
                       <span className="font-medium text-lg text-foreground">Click to upload an image</span>
                       <span className="text-sm">PNG, JPG up to 10MB</span>
                    </>
                )}
                <input type="file" className="hidden" accept="image/*" ref={fileInputRef} onChange={handleImageChange} />
            </CardContent>
        </Card>

        {imagePreview && (
             <Button onClick={handleRun} disabled={loading} size="lg" className="w-full max-w-xs">
                 {loading ? <Loader2 className="animate-spin h-5 w-5 mr-2" /> : <ImageIcon className="h-5 w-5 mr-2" />}
                 Run Vision Inference
             </Button>
        )}

        {result && (
            <Card className="w-full bg-primary/5 border-primary/20">
                <CardContent className="p-6">
                     <div className="flex justify-between items-center mb-4">
                        <span className="text-sm text-muted-foreground">Result</span>
                        <Badge variant="default" className="text-lg px-3 py-1">{result.output}</Badge>
                    </div>
                </CardContent>
            </Card>
        )}
    </div>
  );
}
