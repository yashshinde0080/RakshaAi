'use client';

import { cn } from '@/lib/utils';
import { Message, RagSource, TriageHint } from '@/types';
import { User, Bot, Copy, Check, Pencil, RefreshCw, FileText, Brain, ChevronDown, Stethoscope, PhoneCall } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence } from 'framer-motion';
import { DocumentViewerModal } from './DocumentViewerModal';

interface MessageListProps {
  messages: Message[];
  onEditMessage?: (index: number) => void;
  onRegenerate?: () => void;
  editingIndex?: number | null;
  isLoading?: boolean;
}

const CodeBlock = ({ inline, className, children }: { inline?: boolean; className?: string; children?: React.ReactNode }) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const isBlock = !inline && match;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isBlock) {
    return (
      <div className="relative group my-4 rounded-lg overflow-hidden border border-border/50 bg-zinc-950">
        <div className="flex items-center justify-between px-4 py-2 bg-zinc-900 border-b border-white/10">
          <span className="text-xs font-mono text-zinc-400">{match[1]}</span>
          <button
            onClick={copyToClipboard}
            className="text-zinc-400 hover:text-white transition-colors"
            title="Copy code"
          >
            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
        <div className="p-4 overflow-x-auto">
          <code className={cn("text-sm text-zinc-100 font-mono", className)}>
            {children}
          </code>
        </div>
      </div>
    );
  }

  return (
    <code className={cn("bg-muted/50 rounded-md px-1.5 py-0.5 text-sm font-mono text-primary", className)}>
      {children}
    </code>
  );
};

// Collapsible reasoning block for assistant messages with a <think> trace.
// Auto-opens while the reasoning is still streaming (live); collapsed once the
// answer starts. The user's own toggle wins either way.
const ThinkingBlock = ({ reasoning, live }: { reasoning: string; live?: boolean }) => {
  const [open, setOpen] = useState(live);
  const [copied, setCopied] = useState(false);

  const copyReasoning = () => {
    navigator.clipboard.writeText(reasoning);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mb-3 rounded-lg border border-border/50 bg-muted/40 overflow-hidden">
      <div className="flex items-center gap-1 px-2 py-1.5">
        <button
          onClick={() => setOpen(!open)}
          className="flex flex-1 min-w-0 items-center gap-2 px-1 py-0.5 text-left text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          title={open ? 'Hide reasoning' : 'Show reasoning'}
          aria-expanded={open}
        >
          <Brain className={cn('h-3.5 w-3.5 shrink-0', live && 'animate-pulse')} />
          <span className="font-semibold tracking-wide">{live ? 'Thinking…' : 'Thinking'}</span>
        </button>
        <button
          onClick={copyReasoning}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title={copied ? 'Copied!' : 'Copy reasoning'}
          aria-label="Copy reasoning"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={() => setOpen(!open)}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title={open ? 'Hide reasoning' : 'Show reasoning'}
          aria-label={open ? 'Hide reasoning' : 'Show reasoning'}
        >
          <ChevronDown
            className={cn('h-3.5 w-3.5 transition-transform duration-200', open && 'rotate-180')}
          />
        </button>
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <pre className="whitespace-pre-wrap px-3 pb-3 text-[12.5px] leading-relaxed font-mono text-muted-foreground/90 border-t border-border/40">
              {reasoning}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Raksha AI guardrail: the triage-agent verdict attached to medical replies.
// Framed as a healthcare helper/instructor — never a doctor.
const SEVERITY_HEX: Record<number, string> = {
  1: '#dc2626',
  2: '#ea580c',
  3: '#d97706',
  4: '#65a30d',
  5: '#16a34a',
};

const TriageCard = ({ hint }: { hint: TriageHint }) => {
  const color = SEVERITY_HEX[hint.severity] ?? SEVERITY_HEX[5];
  return (
    <div className="mt-3 rounded-xl border border-brand/30 bg-brand/5 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand">
          <Stethoscope className="h-3.5 w-3.5" />
          Healthcare Helper — not a doctor
        </span>
        <span
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold text-white"
          style={{ backgroundColor: color }}
        >
          ESI Level {hint.severity}
        </span>
      </div>
      <p className="mt-1.5 text-sm font-medium">{hint.label}</p>
      <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
        {hint.recommended_action}
      </p>
      {hint.reasons.length > 0 && (
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          {hint.reasons.join(' · ')}
        </p>
      )}
      {hint.is_emergency && (
        <a
          href="tel:112"
          className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-destructive px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-destructive/90"
        >
          <PhoneCall className="h-3 w-3" />
          Call 112 now
        </a>
      )}
    </div>
  );
};

const CopyMessageButton = ({ text, className }: { text: string; className?: string }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={copyToClipboard}
      className={cn(
        "absolute bottom-2 right-2 p-1.5 rounded-md transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100",
        className
      )}
      title={copied ? 'Copied!' : 'Copy message'}
      aria-label="Copy message"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
};

export function MessageList({ messages, onEditMessage, onRegenerate, editingIndex, isLoading }: MessageListProps) {
  const [viewSource, setViewSource] = useState<RagSource | null>(null);

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="bg-primary/5 p-6 rounded-full mb-6 relative overflow-hidden group"
        >
          <div className="absolute inset-0 bg-primary/10 group-hover:bg-primary/20 transition-colors rounded-full animate-pulse" />
          <Bot className="h-16 w-16 text-primary relative z-10" />
        </motion.div>
        <motion.h3 
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="text-xl font-medium text-foreground mb-2"
        >
          How can I help you today?
        </motion.h3>
        <motion.p 
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-sm max-w-sm"
        >
          Engage in a conversation with your downloaded AI model.
        </motion.p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-2">
      <DocumentViewerModal
        source={viewSource}
        open={viewSource !== null}
        onOpenChange={(open) => !open && setViewSource(null)}
      />
      <AnimatePresence initial={false}>
        {messages.map((message, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className={cn(
              'flex gap-4 w-full',
              message.role === 'user' ? 'justify-end md:pl-20' : 'justify-start md:pr-20'
            )}
          >
            {message.role === 'assistant' && (
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 border border-primary/20 shadow-sm mt-1">
                <Bot className="h-5 w-5 text-primary" />
              </div>
            )}
            
            <div
              className={cn(
                'rounded-2xl px-5 py-3.5 shadow-sm text-[15px] leading-relaxed relative group transition-shadow duration-300',
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-tr-sm'
                  : 'bg-card border border-border/50 text-foreground rounded-tl-sm w-full prose prose-sm md:prose-base prose-zinc dark:prose-invert max-w-none',
                index === editingIndex && message.role === 'user' &&
                  'ring-2 ring-brand-accent/50 ring-offset-2 ring-offset-background shadow-md'
              )}
            >
              <CopyMessageButton
                text={message.content}
                className={
                  message.role === 'user'
                    ? 'text-primary-foreground/70 hover:text-primary-foreground hover:bg-primary-foreground/15'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                }
              />
              {message.role === 'user' && onEditMessage && (
                <button
                  onClick={() => onEditMessage(index)}
                  disabled={isLoading}
                  className={cn(
                    'absolute bottom-2 right-9 p-1.5 rounded-md text-primary-foreground/70 hover:text-primary-foreground hover:bg-primary-foreground/15 transition-colors disabled:opacity-0',
                    index === editingIndex
                      ? 'opacity-100'
                      : 'opacity-0 group-hover:opacity-100 focus:opacity-100'
                  )}
                  title="Edit message"
                  aria-label="Edit message"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
              {message.role === 'user' ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <>
                {message.reasoning && (
                  <ThinkingBlock
                    reasoning={message.reasoning}
                    live={isLoading && index === messages.length - 1 && !message.content.trim()}
                  />
                )}
                {message.role === 'assistant' && message.triage && (
                  <TriageCard hint={message.triage} />
                )}
                {!message.content.trim() && !message.reasoning &&
                  isLoading && index === messages.length - 1 && (
                    <p className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                      <Brain className="h-4 w-4" />
                      Thinking…
                    </p>
                  )}
                {message.reasoning && !message.content.trim() &&
                  !(isLoading && index === messages.length - 1) && (
                    <p className="text-sm text-muted-foreground">
                      The model stopped thinking before producing an answer — try
                      asking again, or turn thinking off for a quicker reply.
                    </p>
                  )}
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code: CodeBlock,
                    p: ({children}) => <p className="mb-4 last:mb-0 leading-7">{children}</p>,
                    ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-2">{children}</ul>,
                    ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-2">{children}</ol>,
                    li: ({children}) => <li>{children}</li>,
                    h1: ({children}) => <h1 className="text-2xl font-semibold mb-4 mt-6 first:mt-0">{children}</h1>,
                    h2: ({children}) => <h2 className="text-xl font-semibold mb-3 mt-6 first:mt-0">{children}</h2>,
                    h3: ({children}) => <h3 className="text-lg font-semibold mb-3 mt-4 first:mt-0">{children}</h3>,
                  }}
                >
                  {message.content}
                </ReactMarkdown>
                </>
              )}

              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/60 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Sources
                  </span>
                  {message.sources.map((source) => (
                    <button
                      key={source.filename}
                      onClick={() => setViewSource(source)}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 pl-2 pr-2.5 py-0.5 text-xs text-primary hover:bg-primary/20 hover:border-primary/40 transition-colors"
                      title={`View ${source.filename}`}
                    >
                      <FileText className="h-3 w-3 shrink-0" />
                      <span className="max-w-[180px] truncate font-medium">{source.filename}</span>
                    </button>
                  ))}
                </div>
              )}

              {message.role === 'assistant' &&
                index === messages.length - 1 &&
                onRegenerate && (
                <button
                  onClick={onRegenerate}
                  disabled={isLoading}
                  className="absolute bottom-2 right-9 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors disabled:opacity-0 group-hover:opacity-100 focus:opacity-100"
                  title="Regenerate response"
                  aria-label="Regenerate response"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {message.role === 'user' && (
              <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center flex-shrink-0 border border-border shadow-sm mt-1">
                <User className="h-5 w-5 text-secondary-foreground" />
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}