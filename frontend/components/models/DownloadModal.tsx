'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Download } from 'lucide-react';
import type { DownloadStatus } from '@/types';

interface DownloadModalProps {
  open: boolean;
  onClose: () => void;
  onDownload: (model: string, quant: string) => Promise<void>;
  downloadStatus: DownloadStatus | null;
}

const popularModels = [
  { id: 'llama3:8b', name: 'Llama 3 8B' },
  { id: 'llama3:70b', name: 'Llama 3 70B' },
  { id: 'mistral:7b', name: 'Mistral 7B' },
  { id: 'microsoft/bitnet-b1.58-2B-4T', name: 'BitNet 1.58B (Microsoft)' },
  { id: 'tdh111/bitnet-b1.58-2B-4T-GGUF', name: 'BitNet 1.58B (GGUF repo)' },
  { id: 'tinyllama:1b', name: 'TinyLlama 1B' },
];

export function DownloadModal({ open, onClose, onDownload, downloadStatus }: DownloadModalProps) {
  const [model, setModel] = useState('');
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    if (!model) return;

    setDownloading(true);
    try {
      // Empty string quantization natively triggers 
      // full repository downloads or best-file selections backend
      await onDownload(model, '');
    } finally {
      setDownloading(false);
    }
  };

  const isOngoing = downloadStatus?.status === 'downloading' || downloadStatus?.status === 'verifying' || downloadStatus?.status === 'encrypting';
  const progress = downloadStatus?.progress || 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Download Model</DialogTitle>
          <DialogDescription>
            Download an entire model repository or a single GGUF file from HuggingFace.
            Full repositories will automatically be downloaded into a dedicated sub-folder.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue placeholder="Select a model" />
              </SelectTrigger>
              <SelectContent>
                {popularModels.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Or enter model name</Label>
            <Input
              placeholder="e.g., llama3:8b"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>

          {isOngoing && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="capitalize">{downloadStatus?.status || 'Downloading'}...</span>
                <span>{progress.toFixed(1)}%</span>
              </div>
              <Progress value={progress} />
              <p className="text-xs text-muted-foreground">
                {downloadStatus?.downloaded_gb?.toFixed(2) || 0} / {downloadStatus?.total_gb?.toFixed(2) || 0} GB
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleDownload} disabled={!model || downloading || isOngoing}>
            <Download className="h-4 w-4 mr-2" />
            {isOngoing ? 'Processing...' : 'Download'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
