'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import { toast } from '@/components/ui/use-toast';
import { Send, X, PencilLine, Plus, Loader2, UploadCloud, HeartPulse } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024; // 50MB — matches the Documents page
const VALID_TYPES = ['.txt', '.pdf'];

interface PromptInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  externalValue?: string;
  editing?: boolean;
  onCancelEdit?: () => void;
  onDocumentAdded?: () => void;
  onUploadSuggestion?: (filename: string) => void;
}

export function PromptInput({ onSend, disabled, externalValue, editing, onCancelEdit, onDocumentAdded, onUploadSuggestion }: PromptInputProps) {
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load an externally-provided value (edit mode) into the textarea; clear
  // when edit mode ends. Keyed on `editing` too so re-editing the same message
  // (identical externalValue) still re-populates after a cancel.
  useEffect(() => {
    if (externalValue !== undefined) {
      setInput(externalValue);
      textareaRef.current?.focus();
    } else {
      setInput('');
    }
  }, [externalValue, editing]);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  // Upload a document straight into the RAG index so chat answers can cite it
  // (chat already sends use_rag: true and renders Sources Used in the stream).
  // Shared by the + button (file input) and drag-and-drop.
  const uploadFile = async (file: File) => {
    if (!file || uploading || disabled) return;

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!VALID_TYPES.includes(ext)) {
      toast({ title: 'Unsupported file type', description: 'Only .txt and .pdf files are accepted.', variant: 'destructive' });
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE) {
      toast({ title: 'File too large', description: `Max upload size is 50MB (got ${(file.size / 1024 / 1024).toFixed(1)}MB).`, variant: 'destructive' });
      return;
    }

    setUploading(true);
    try {
      await api.uploadDocument(file);
      onDocumentAdded?.();
      onUploadSuggestion?.(file.name);
      toast({ title: 'Document added to chat', description: `"${file.name}" is now indexed for RAG. Ask about it in the chat.` });
    } catch (error) {
      toast({ title: 'Upload failed', description: error instanceof Error ? error.message : String(error), variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow re-selecting the same file
    if (file) await uploadFile(file);
  };

  // ponytail: native HTML5 drag-drop via React props (no library, no stale
  // closures — synthetic events always use the latest render's handlers).
  const handleDragEnter = (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); if (!disabled) setDragging(true); };
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); if (!disabled) setDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (!containerRef.current?.contains(e.relatedTarget as Node)) setDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void uploadFile(file);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div
      ref={containerRef}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'relative flex flex-col gap-2 bg-background border shadow-sm rounded-2xl p-2 transition-all',
        dragging
          ? 'border-primary ring-2 ring-primary/30 bg-primary/5 scale-[1.01]'
          : 'border-border focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary'
      )}
    >
      {dragging && (
        <div className="pointer-events-none absolute inset-0 z-10 rounded-2xl flex items-center justify-center bg-primary/10 backdrop-blur-[1px]">
          <span className="text-sm font-medium text-primary flex items-center gap-2">
            <UploadCloud className="h-4 w-4" />
            Drop to add to chat (RAG)
          </span>
        </div>
      )}
      {editing && (
        <div className="flex items-center justify-between px-1 pt-0.5">
          <span className="text-[11px] font-medium text-primary/80 flex items-center gap-1.5">
            <PencilLine className="h-3 w-3" />
            Editing message — send to re-run
          </span>
          <button
            onClick={onCancelEdit}
            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            title="Cancel edit"
            aria-label="Cancel edit"
          >
            <X className="h-3 w-3" />
            Cancel
          </button>
        </div>
      )}
      <div className="flex items-end gap-2">
          {/* Raksha AI — jump straight into a medical triage run. The chat
              conversation persists in localStorage, so nothing is lost. */}
          <Link
            href="/triage"
            title="Start a Raksha AI medical triage (ESI)"
            aria-label="Start a Raksha AI medical triage"
            className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-xl bg-brand px-3 text-xs font-semibold text-white shadow-sm transition-all hover:bg-brand/90 hover:shadow-md active:scale-95"
          >
            <HeartPulse className="h-4 w-4" />
            Triage
          </Link>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf"
            className="hidden"
            onChange={handleFile}
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || uploading}
            size="icon"
            variant="ghost"
            className="h-9 w-9 shrink-0 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
            title={uploading ? 'Uploading...' : 'Add a document to chat (RAG)'}
            aria-label={uploading ? 'Uploading document' : 'Add a document to chat'}
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          </Button>
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message the model... (Shift+Enter for newline)"
            disabled={disabled}
            className="min-h-[44px] max-h-[200px] resize-none border-0 focus-visible:ring-0 shadow-none px-3 py-3 bg-transparent w-full text-[15px]"
            rows={1}
          />
          <div className="flex-shrink-0 h-11 flex items-center mb-[2px]">
            <Button 
              onClick={handleSubmit} 
              disabled={disabled || !input.trim()}
              size="icon"
              className={cn(
                "h-9 w-9 rounded-xl transition-all duration-300",
                input.trim() 
                  ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-md scale-100" 
                  : "bg-muted text-muted-foreground scale-95 opacity-50"
              )}
            >
              <Send className={cn("h-4 w-4", input.trim() && "ml-0.5")} />
            </Button>
          </div>
        </div>
    </div>
  );
}