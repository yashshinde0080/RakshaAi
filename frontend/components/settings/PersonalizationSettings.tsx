"use client";

import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Save } from "lucide-react";
import { CharacteristicChip } from "./CharacteristicChip";

interface PersonalizationSettingsProps {
  data: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

const STYLES = [
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "formal", label: "Formal" },
  { value: "friendly", label: "Friendly" },
  { value: "concise", label: "Concise" },
  { value: "detailed", label: "Detailed" },
  { value: "academic", label: "Academic" },
  { value: "creative", label: "Creative" },
];

const CHARACTERISTICS = [
  "default",
  "warm",
  "enthusiastic",
  "cynical",
  "humorous",
  "direct",
  "empathetic",
  "analytical",
  "encouraging",
  "sarcastic",
];

const HEADERS_LISTS = [
  { value: "default", label: "Default" },
  { value: "always", label: "Always" },
  { value: "never", label: "Never" },
  { value: "minimal", label: "Minimal" },
];

const RESPONSE_LENGTHS = [
  { value: "default", label: "Default" },
  { value: "short", label: "Short" },
  { value: "medium", label: "Medium" },
  { value: "long", label: "Long" },
  { value: "detailed", label: "Detailed" },
];

export function PersonalizationSettings({
  data,
  onSave,
}: PersonalizationSettingsProps) {
  const [form, setForm] = useState({
    base_style_tone: "professional",
    characteristics: ["default"],
    headers_lists_mode: "default",
    response_length: "default",
    custom_instructions: "",
    user_context: "",
    preferred_name: "",
    profession: "",
    interests: [] as string[],
    ...data,
  });

  const [interestInput, setInterestInput] = useState("");

  // ponytail: React-blessed "adjust state during render" — replaces the old
  // useEffect(() => setForm(...), [data]) sync without the set-state-in-effect rule hit
  const [prevData, setPrevData] = useState(data);
  if (prevData !== data) {
    setPrevData(data);
    setForm((prev) => ({ ...prev, ...data }));
  }

  const update = (key: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [key]: value }) as typeof form);
  };

  const toggleCharacteristic = (char: string) => {
    const current = form.characteristics as string[];
    if (char === "default") {
      update("characteristics", ["default"]);
      return;
    }
    const withoutDefault = current.filter((c) => c !== "default");
    if (withoutDefault.includes(char)) {
      const remaining = withoutDefault.filter((c) => c !== char);
      update("characteristics", remaining.length > 0 ? remaining : ["default"]);
    } else {
      update("characteristics", [...withoutDefault, char]);
    }
  };

  const addInterest = () => {
    if (interestInput.trim() && !form.interests.includes(interestInput.trim())) {
      update("interests", [...form.interests, interestInput.trim()]);
      setInterestInput("");
    }
  };

  const removeInterest = (interest: string) => {
    update(
      "interests",
      form.interests.filter((i: string) => i !== interest)
    );
  };

  return (
    <div className="space-y-6">
      {/* Base Style and Tone */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Base Style & Tone
        </h3>
        <p className="text-xs text-slate-500">
          Set the style and tone of how the AI responds to you. This doesn&apos;t
          impact capabilities.
        </p>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Style</Label>
          <Select
            value={form.base_style_tone}
            onValueChange={(v) => update("base_style_tone", v)}
          >
            <SelectTrigger className="w-[180px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              {STYLES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Characteristics */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Characteristics
        </h3>
        <p className="text-xs text-slate-500">
          Choose additional customizations on top of your base style and tone.
        </p>
        <div className="flex flex-wrap gap-2">
          {CHARACTERISTICS.map((char) => (
            <CharacteristicChip
              key={char}
              label={char}
              selected={(form.characteristics as string[]).includes(char)}
              onClick={() => toggleCharacteristic(char)}
            />
          ))}
        </div>
      </div>

      {/* Response Format */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Response Format
        </h3>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Headers & Lists</Label>
          <Select
            value={form.headers_lists_mode}
            onValueChange={(v) => update("headers_lists_mode", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              {HEADERS_LISTS.map((h) => (
                <SelectItem key={h.value} value={h.value}>
                  {h.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Response Length</Label>
          <Select
            value={form.response_length}
            onValueChange={(v) => update("response_length", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              {RESPONSE_LENGTHS.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* About You */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          About You
        </h3>

        <div className="space-y-2">
          <Label className="text-sm text-slate-300">Preferred Name</Label>
          <Input
            className="bg-slate-900 border-slate-700"
            placeholder="How should the AI address you?"
            value={form.preferred_name}
            onChange={(e) => update("preferred_name", e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label className="text-sm text-slate-300">Profession</Label>
          <Input
            className="bg-slate-900 border-slate-700"
            placeholder="e.g. Software Engineer, Student, Doctor"
            value={form.profession}
            onChange={(e) => update("profession", e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label className="text-sm text-slate-300">Interests</Label>
          <div className="flex gap-2">
            <Input
              className="bg-slate-900 border-slate-700 flex-1"
              placeholder="Add an interest"
              value={interestInput}
              onChange={(e) => setInterestInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addInterest()}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={addInterest}
              className="bg-slate-800"
            >
              Add
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {form.interests.map((interest: string) => (
              <span
                key={interest}
                className="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs cursor-pointer hover:bg-red-900/30 hover:text-red-400 transition-colors"
                onClick={() => removeInterest(interest)}
              >
                {interest} ×
              </span>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm text-slate-300">
            Context About You
          </Label>
          <Textarea
            className="bg-slate-900 border-slate-700 min-h-[80px]"
            placeholder="Any other context the AI should know about you..."
            value={form.user_context}
            onChange={(e) => update("user_context", e.target.value)}
          />
        </div>
      </div>

      {/* Custom Instructions */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Custom Instructions
        </h3>
        <p className="text-xs text-slate-500">
          Provide specific instructions that will be included in every
          conversation.
        </p>
        <Textarea
          className="bg-slate-900 border-slate-700 min-h-[120px] font-mono text-sm"
          placeholder="e.g. Always provide code examples in Python. Avoid using jargon unless I ask for it."
          value={form.custom_instructions}
          onChange={(e) => update("custom_instructions", e.target.value)}
        />
      </div>

      <Button
        onClick={() => onSave(form)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        <Save className="h-4 w-4 mr-2" />
        Save Personalization
      </Button>
    </div>
  );
}