'use client';

import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api } from '@/lib/api';
import { errMsg } from '@/lib/utils';
import { FileText, Loader2, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import type { RagSource } from '@/types';

interface Chunk {
  chunk_index: number;
  content: string;
  metadata: Record<string, unknown>;
}

interface DocumentViewerModalProps {
  source: RagSource | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentViewerModal({ source, open, onOpenChange }: DocumentViewerModalProps) {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !source) return;
    // Legacy sources (pre-document_id) can't be fetched — show a helpful hint.
    if (!source.document_id) {
      setChunks([]);
      setError(`No stored preview for "${source.filename}". Open it in Documents instead.`);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getDocumentChunks(source.document_id)
      .then((res) => {
        if (!cancelled) setChunks(res.chunks || []);
      })
      .catch((e) => {
        if (!cancelled) setError(errMsg(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, source]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col p-0 overflow-hidden gap-0">
        <DialogHeader className="px-6 pt-5 pb-3 border-b border-border/60">
          <DialogTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-primary shrink-0" />
            <span className="truncate">{source?.filename ?? 'Document'}</span>
          </DialogTitle>
          <DialogDescription>
            {loading
              ? 'Loading chunks...'
              : chunks.length > 0
                ? `${chunks.length} chunk${chunks.length !== 1 ? 's' : ''} in the RAG index`
                : 'Source document'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Loading document chunks...
            </div>
          ) : error ? (
            <div className="px-6 py-8 text-sm text-destructive">{error}</div>
          ) : chunks.length === 0 ? (
            <div className="px-6 py-8 text-sm text-muted-foreground">No chunks found for this document.</div>
          ) : (
            <ScrollArea className="max-h-[50vh]">
              <div className="space-y-3 px-6 py-4">
                {chunks.map((chunk) => (
                  <div key={chunk.chunk_index} className="rounded-lg border border-border/50 bg-muted/30 p-3">
                    <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-1.5">
                      Chunk {chunk.chunk_index + 1}
                    </div>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-3 border-t border-border/60">
          <p className="text-xs text-muted-foreground">
            {source?.document_id ? `ID: ${source.document_id.slice(0, 24)}…` : 'Indexed in the RAG store'}
          </p>
          <Link
            href={`/documents${source?.filename ? `?file=${encodeURIComponent(source.filename)}` : ''}`}
            onClick={() => onOpenChange(false)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
          >
            Open in Documents
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </DialogContent>
    </Dialog>
  );
}
