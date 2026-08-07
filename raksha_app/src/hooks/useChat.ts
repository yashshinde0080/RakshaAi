import { useCallback, useRef, useState } from 'react';

import { streamChat } from '@/api';
import type { Message, RagSource } from '@/types';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [enableThinking, setEnableThinking] = useState(true);
  const sendingRef = useRef(false);

  const send = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || sendingRef.current) return;

      const history: Message[] = [...messages, { role: 'user', content: trimmed }];
      sendingRef.current = true;
      setIsLoading(true);
      setMessages([...history, { role: 'assistant', content: '' }]);

      let text = '';
      let reasoning = '';
      let sources: RagSource[] | undefined;

      const patch = (extra: Partial<Message> = {}) => {
        setMessages((prev) => {
          const next = [...prev];
          // Chat was cleared while the stream was in flight — drop the patch.
          if (next.length === 0) return next;
          next[next.length - 1] = {
            role: 'assistant',
            content: text,
            ...(reasoning ? { reasoning } : {}),
            ...(sources ? { sources } : {}),
            ...extra,
          };
          return next;
        });
      };

      const finish = () => {
        // Model stopped mid-think (reasoning but no answer) → surface the
        // reasoning as the reply so the bubble is never empty.
        if (!text.trim() && reasoning.trim()) {
          text = reasoning;
          reasoning = '';
        }
        patch();
        sendingRef.current = false;
        setIsLoading(false);
      };

      streamChat(history, enableThinking, (d) => {
        if (d.error) {
          patch({ content: `**Error:** ${d.error}` });
          sendingRef.current = false;
          setIsLoading(false);
          return;
        }
        if (d.reasoning) reasoning += d.reasoning;
        if (d.content) text += d.content;
        if (d.sources?.length) {
          const seen = new Set<string>();
          sources = d.sources.filter((s) => {
            if (seen.has(s.filename)) return false;
            seen.add(s.filename);
            return true;
          });
        }
        if (d.content || d.reasoning || d.sources?.length) patch();
        if (d.done) finish();
      });
    },
    [messages, enableThinking]
  );

  const clear = useCallback(() => setMessages([]), []);

  return { messages, isLoading, enableThinking, setEnableThinking, send, clear };
}
