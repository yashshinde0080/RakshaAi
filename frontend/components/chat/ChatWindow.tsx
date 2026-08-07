'use client';

import { useEffect, useRef, useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageList } from './MessageList';
import { Message } from '@/types';
import { ArrowDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  editingIndex?: number | null;
  onEditMessage?: (index: number) => void;
  onRegenerate?: () => void;
}

export function ChatWindow({ messages, isLoading, editingIndex, onEditMessage, onRegenerate }: ChatWindowProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const lastScrollTop = useRef(0);
  const scrollAnimRef = useRef<number | null>(null);
  const lastAnimatedTop = useRef<number | null>(null);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const [pillHovered, setPillHovered] = useState(false);

  // Auto-scroll to the newest message while streaming, unless the user has
  // scrolled up to read history (stickToBottom flips off on manual scroll).
  // Submitting a new message always jumps back to the bottom, and the freshly
  // added empty assistant placeholder re-pins when the answer starts streaming
  // (covers auto-sent deep-link questions whose reply lands after a slow fetch).
  useEffect(() => {
    const viewport = viewportRef.current;
    const last = messages[messages.length - 1];
    if (last?.role === 'user' || (last?.role === 'assistant' && last.content === '')) {
      stickToBottom.current = true;
    }
    if (viewport && stickToBottom.current) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const onScroll = () => {
      const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      stickToBottom.current = distanceFromBottom < 80;
      // Cancel the rAF jump if anything moves the viewport off the
      // animation's expected position — the user's wheel/touch, or a
      // programmatic pin from a new token — so the loop never fights them.
      if (
        scrollAnimRef.current !== null &&
        lastAnimatedTop.current !== null &&
        Math.abs(viewport.scrollTop - lastAnimatedTop.current) > 1
      ) {
        cancelAnimationFrame(scrollAnimRef.current);
        scrollAnimRef.current = null;
      }
      // Direction-aware pill: surface only while scrolling up (away from the
      // latest message); any downward scroll hides it — the user is already
      // heading back to the bottom, so the button is just clutter.
      const scrollingUp = viewport.scrollTop < lastScrollTop.current;
      lastScrollTop.current = viewport.scrollTop;
      if (scrollingUp && distanceFromBottom >= 80) {
        setShowJumpToLatest(true);
      } else if (!scrollingUp) {
        setShowJumpToLatest(false);
      }
    };
    viewport.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      viewport.removeEventListener('scroll', onScroll);
      if (scrollAnimRef.current !== null) cancelAnimationFrame(scrollAnimRef.current);
    };
  }, []);

  // Auto-hide the pill a few seconds after it appears so it doesn't linger
  // while the user reads; the next upward scroll brings it back. Hovering
  // pauses the countdown — leaving restarts a fresh one.
  useEffect(() => {
    if (!showJumpToLatest || pillHovered) return;
    const timer = window.setTimeout(() => setShowJumpToLatest(false), 3000);
    return () => window.clearTimeout(timer);
  }, [showJumpToLatest, pillHovered]);

  const jumpToLatest = () => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    stickToBottom.current = true;
    setShowJumpToLatest(false);

    // Cancel any in-flight animation (rapid re-clicks).
    if (scrollAnimRef.current !== null) {
      cancelAnimationFrame(scrollAnimRef.current);
      scrollAnimRef.current = null;
    }

    const startTop = viewport.scrollTop;
    lastAnimatedTop.current = startTop; // keep the guard's baseline in sync
    const endTop = viewport.scrollHeight;
    if (endTop <= startTop) return;

    // Respect reduced-motion: jump instantly instead of animating.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      viewport.scrollTop = endTop;
      return;
    }

    // Exact 200ms ease-out cubic scroll. The onScroll listener cancels the
    // loop if anything moves the viewport off the animation's position, so
    // we never fight the user (or a token pin).
    const DURATION = 200;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min((now - start) / DURATION, 1);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      const top = startTop + (endTop - startTop) * eased;
      lastAnimatedTop.current = top;
      viewport.scrollTop = top;
      if (t < 1) {
        scrollAnimRef.current = requestAnimationFrame(step);
      } else {
        scrollAnimRef.current = null;
        // Re-read: content may have grown mid-animation.
        viewport.scrollTop = viewport.scrollHeight;
      }
    };
    scrollAnimRef.current = requestAnimationFrame(step);
  };

  return (
    <div className="relative flex-1 min-h-0 w-full">
      <ScrollArea
        viewportRef={viewportRef}
        type="always"
        className="h-full w-full px-4 md:px-8 py-4"
        scrollBarClassName="w-1.5"
        thumbClassName="bg-brand/70 hover:bg-brand active:bg-brand-accent transition-colors"
      >
        <div className="max-w-4xl mx-auto w-full">
          <MessageList
            messages={messages}
            onEditMessage={onEditMessage}
            onRegenerate={onRegenerate}
            editingIndex={editingIndex}
            isLoading={isLoading}
          />
          {isLoading && (
            <div className="flex items-center gap-3 text-muted-foreground mt-4 mb-8">
              <div className="flex gap-1.5 px-3 py-2.5 bg-muted/50 rounded-2xl w-fit">
                <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Floating pill shown while the user has scrolled up from the latest message */}
      <AnimatePresence>
        {showJumpToLatest && (
          <motion.button
            initial={{ opacity: 0, y: 8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.9 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={jumpToLatest}
            onMouseEnter={() => setPillHovered(true)}
            onMouseLeave={() => setPillHovered(false)}
            className="absolute bottom-4 right-4 md:right-8 inline-flex items-center gap-1.5 rounded-full bg-primary text-primary-foreground pl-2.5 pr-3 py-2 text-xs font-medium shadow-lg shadow-primary/25 hover:bg-primary/90 transition-colors"
            title="Jump to latest"
            aria-label="Jump to latest"
          >
            {/* One-shot bounce on the arrow each time the pill appears */}
            <motion.span
              animate={{ y: [0, -4, 0, -2, 0] }}
              transition={{ duration: 0.7, delay: 0.1, ease: 'easeInOut' }}
              className="inline-flex"
            >
              <ArrowDown className="h-3.5 w-3.5" />
            </motion.span>
            Jump to latest
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}