'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { PromptInput } from '@/components/chat/PromptInput';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useChat } from '@/hooks/useChat';
import { Switch } from '@/components/ui/switch';
import { api } from '@/lib/api';
import { toast } from '@/components/ui/use-toast';
import { Download, Trash2, FileText, X, Sparkles, Brain } from 'lucide-react';
import { errMsg } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

interface RAGDoc {
  id: string;
  filename: string;
  chunks: number;
  created_at: string;
}

interface ChatModuleProps {
  taskType: string;
  model: string;
  /** Deep-link from Documents: auto-sends an ask-about query once on mount. */
  initialAsk?: string;
}

export function ChatModule({ taskType, model, initialAsk }: ChatModuleProps) {
  const autoAskSent = useRef(false);
  const {
    messages,
    isLoading,
    enableThinking,
    setEnableThinking,
    sendMessage,
    editAndResend,
    regenerate,
    clearMessages,
    exportChat,
  } = useChat();
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [docs, setDocs] = useState<RAGDoc[]>([]);
  const [suggestion, setSuggestion] = useState<string | null>(null);

  // The RAG index is global and chat queries it (use_rag: true), so the chips
  // mirror the full index. Load on mount, silently refresh after uploads.
  const refreshDocs = useCallback(async () => {
    try {
      const res = await api.listDocuments();
      setDocs(res.documents || []);
    } catch {
      // backend unreachable — chips stay empty, chat still works
    }
  }, []);

  useEffect(() => {
    refreshDocs();
  }, [refreshDocs]);

  // Deep-link from Documents (/console?ask=<file>): send the question once
  // when the chat mounts. Ref-guarded so React StrictMode's double-mount can't
  // fire it twice.
  useEffect(() => {
    if (initialAsk && !autoAskSent.current) {
      autoAskSent.current = true;
      toast({
        title: `Asking about '${initialAsk}'...`,
        description: 'Your question was sent automatically.',
      });
      sendMessage(`Ask about '${initialAsk}'`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUploadSuggestion = (filename: string) => {
    setSuggestion(filename);
  };

  const handleAskAboutDoc = () => {
    if (!suggestion) return;
    handleSend(`Ask about '${suggestion}'`);
    setSuggestion(null);
  };

  const handleDeleteDoc = async (docId: string, filename: string) => {
    if (!window.confirm(`Remove "${filename}" from the chat index? This deletes it from the RAG store.`)) return;
    try {
      await api.deleteDocument(docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      toast({ title: 'Document removed', description: filename });
    } catch (error) {
      toast({ title: 'Remove failed', description: errMsg(error), variant: 'destructive' });
    }
  };

  const handleSend = (text: string) => {
    if (editingIndex !== null) {
      editAndResend(editingIndex, text);
      setEditingIndex(null);
    } else {
      sendMessage(text);
    }
  };

  const handleClear = () => {
    clearMessages();
    setEditingIndex(null);
    setSuggestion(null);
  };

  const handleRegenerate = () => {
    setEditingIndex(null);
    regenerate();
  };

  const handleExport = () => {
    toast({
      title: 'Exporting conversation',
      description: 'Your chat is being saved as a markdown file.',
    });
    exportChat();
  };

  return (
    <div className="flex flex-col h-full bg-background rounded-b-2xl">
      {/* Chat action bar */}
      {messages.length > 0 && (
        <div className="flex items-center gap-1.5 px-4 pt-2.5 justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExport}
            disabled={isLoading}
            className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60"
            title="Export conversation as markdown"
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            Export
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                disabled={isLoading}
                className="h-7 px-2.5 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                title="Start a new chat"
              >
                <Trash2 className="h-3.5 w-3.5 mr-1" />
                New chat
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent size="sm">
              <AlertDialogHeader>
                <AlertDialogTitle>Start a new chat?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently deletes the current conversation and its saved
                  history from this browser.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  variant="destructive"
                  onClick={handleClear}
                >
                  New chat
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          editingIndex={editingIndex}
          onEditMessage={(index) => setEditingIndex(index)}
          onRegenerate={handleRegenerate}
        />
      </div>

      <div className="p-4 mx-auto w-full max-w-4xl bg-gradient-to-t from-background via-background to-transparent pt-6">
        {/* RAG documents attached to this chat — removable chips */}
        {docs.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mr-1">
              In chat
            </span>
            {docs.map((doc) => (
              <span
                key={doc.id}
                className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 pl-2.5 pr-1 py-1 text-xs text-primary hover:bg-primary/15 transition-colors"
                title={`${doc.filename} — ${doc.chunks} chunk${doc.chunks !== 1 ? 's' : ''}`}
              >
                <FileText className="h-3 w-3" />
                <span className="max-w-[180px] truncate font-medium">{doc.filename}</span>
                <button
                  onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                  disabled={isLoading}
                  className="rounded-full p-0.5 text-primary/60 hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-40"
                  title={`Remove ${doc.filename}`}
                  aria-label={`Remove ${doc.filename}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        {/* One-shot suggestion after an upload — click to ask, X to dismiss */}
        <AnimatePresence>
          {suggestion && (
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.97 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="mb-2 flex items-center gap-1.5"
            >
              <button
                onClick={handleAskAboutDoc}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 rounded-full bg-brand-accent/10 border border-brand-accent/30 pl-2.5 pr-2 py-1 text-xs text-brand-accent hover:bg-brand-accent/20 transition-colors disabled:opacity-40"
                title={`Ask the model about '${suggestion}'`}
              >
                <Sparkles className="h-3 w-3" />
                <span className="max-w-[220px] truncate font-medium">Ask about '{suggestion}'</span>
              </button>
              <button
                onClick={() => setSuggestion(null)}
                className="rounded-full p-0.5 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                title="Dismiss suggestion"
                aria-label="Dismiss suggestion"
              >
                <X className="h-3 w-3" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
        {/* Thinking toggle — reasoning models (Qwen3.5 etc.) emit a
            <think> trace when enabled; the backend strips it from content
            and streams it separately so it renders in a collapsible block. */}
        <div className="mb-2 flex items-center justify-end gap-2 px-1">
          <label
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors"
            title="Let reasoning models think out loud before answering"
          >
            <Brain className="h-3.5 w-3.5" />
            Thinking
          </label>
          <Switch
            checked={enableThinking}
            onCheckedChange={setEnableThinking}
            aria-label="Toggle thinking mode"
          />
        </div>
        <PromptInput
          onSend={handleSend}
          disabled={isLoading}
          externalValue={editingIndex !== null ? messages[editingIndex]?.content : undefined}
          editing={editingIndex !== null}
          onCancelEdit={() => setEditingIndex(null)}
          onDocumentAdded={refreshDocs}
          onUploadSuggestion={handleUploadSuggestion}
        />
        <div className="text-center mt-3 text-xs text-muted-foreground font-medium">
          Task: {taskType === 'unknown' ? 'Generative Chat' : taskType.replace(/_/g, ' ')} | AI can make mistakes. Verify important information.

        </div>
      </div>
    </div>
  );
}
