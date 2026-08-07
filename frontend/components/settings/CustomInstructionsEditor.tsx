"use client";

import React from "react";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface CustomInstructionsEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function CustomInstructionsEditor({
  value,
  onChange,
  disabled = false,
}: CustomInstructionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-sm text-slate-300 font-semibold">
          Custom Instructions
        </Label>
        <p className="text-xs text-slate-500 mt-1">
          These instructions are prepended to every conversation. Use them to
          define how the AI should behave, what to focus on, or what to avoid.
        </p>
      </div>

      <Textarea
        className="bg-slate-900 border-slate-700 min-h-[200px] font-mono text-sm leading-relaxed"
        placeholder={`Example instructions:

- Always respond in bullet points
- Use simple language, avoid jargon
- When writing code, include comments
- Focus on practical solutions
- If uncertain, say so clearly
- Prefer Python for code examples`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{value.length} characters</span>
        <span>Applied to all conversations</span>
      </div>
    </div>
  );
}