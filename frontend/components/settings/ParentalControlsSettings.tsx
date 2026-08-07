"use client";

import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Save, Lock, ShieldAlert } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

interface ParentalControlsSettingsProps {
  data: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

export function ParentalControlsSettings({
  data,
  onSave,
}: ParentalControlsSettingsProps) {
  const [form, setForm] = useState({
    enabled: false,
    content_filter_level: "off",
    block_explicit_content: false,
    restrict_topics: [] as string[],
    max_session_duration_minutes: 0,
    allowed_models: [] as string[],
    disable_custom_instructions: false,
    require_pin_for_settings: false,
    activity_log: false,
    ...data,
  });

  const [newPin, setNewPin] = useState("");
  const [topicInput, setTopicInput] = useState("");
  const [modelInput, setModelInput] = useState("");
  const { toast } = useToast();

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

  const handleSetPin = async () => {
    if (newPin.length < 4) {
      toast({
        title: "Error",
        description: "PIN must be at least 4 digits",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.setParentalPin(newPin);
      toast({ title: "PIN Set", description: "Parental control PIN has been set" });
      setNewPin("");
      update("require_pin_for_settings", true);
    } catch {
      toast({
        title: "Error",
        description: "Failed to set PIN",
        variant: "destructive",
      });
    }
  };

  const addTopic = () => {
    if (topicInput.trim() && !form.restrict_topics.includes(topicInput.trim())) {
      update("restrict_topics", [...form.restrict_topics, topicInput.trim()]);
      setTopicInput("");
    }
  };

  const removeTopic = (topic: string) => {
    update(
      "restrict_topics",
      form.restrict_topics.filter((t: string) => t !== topic)
    );
  };

  const addModel = () => {
    if (modelInput.trim() && !form.allowed_models.includes(modelInput.trim())) {
      update("allowed_models", [...form.allowed_models, modelInput.trim()]);
      setModelInput("");
    }
  };

  const removeModel = (model: string) => {
    update(
      "allowed_models",
      form.allowed_models.filter((m: string) => m !== model)
    );
  };

  return (
    <div className="space-y-6">
      {/* Master Toggle */}
      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-5 w-5 text-amber-500" />
            <div>
              <Label className="text-sm text-slate-300 font-semibold">
                Enable Parental Controls
              </Label>
              <p className="text-xs text-slate-500">
                Restrict content and features for safety
              </p>
            </div>
          </div>
          <Switch
            checked={form.enabled}
            onCheckedChange={(v) => update("enabled", v)}
          />
        </div>
      </div>

      {form.enabled && (
        <>
          {/* PIN Protection */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              PIN Protection
            </h3>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm text-slate-300">
                  Require PIN for settings
                </Label>
                <p className="text-xs text-slate-500">
                  Prevent changes without PIN
                </p>
              </div>
              <Switch
                checked={form.require_pin_for_settings}
                onCheckedChange={(v) => update("require_pin_for_settings", v)}
              />
            </div>

            <div className="flex gap-2">
              <Input
                type="password"
                className="bg-slate-900 border-slate-700 flex-1"
                placeholder="Set PIN (min 4 digits)"
                value={newPin}
                onChange={(e) => setNewPin(e.target.value)}
                maxLength={8}
              />
              <Button
                variant="secondary"
                size="sm"
                className="bg-slate-800"
                onClick={handleSetPin}
              >
                <Lock className="h-4 w-4 mr-1" />
                Set PIN
              </Button>
            </div>
          </div>

          {/* Content Filtering */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Content Filtering
            </h3>

            <div className="flex items-center justify-between">
              <Label className="text-sm text-slate-300">
                Content filter level
              </Label>
              <Select
                value={form.content_filter_level}
                onValueChange={(v) => update("content_filter_level", v)}
              >
                <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700">
                  <SelectItem value="off">Off</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="strict">Strict</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm text-slate-300">
                  Block explicit content
                </Label>
                <p className="text-xs text-slate-500">
                  Filter out adult or violent content
                </p>
              </div>
              <Switch
                checked={form.block_explicit_content}
                onCheckedChange={(v) => update("block_explicit_content", v)}
              />
            </div>

            {/* Restricted Topics */}
            <div className="space-y-2">
              <Label className="text-sm text-slate-300">Restricted Topics</Label>
              <div className="flex gap-2">
                <Input
                  className="bg-slate-900 border-slate-700 flex-1"
                  placeholder="Add topic to restrict"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTopic()}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  className="bg-slate-800"
                  onClick={addTopic}
                >
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {form.restrict_topics.map((topic: string) => (
                  <span
                    key={topic}
                    className="px-3 py-1 rounded-full bg-red-950/30 text-red-400 text-xs cursor-pointer hover:bg-red-900/40 transition-colors border border-red-500/20"
                    onClick={() => removeTopic(topic)}
                  >
                    {topic} ×
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Restrictions */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Restrictions
            </h3>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm text-slate-300">
                  Max session duration
                </Label>
                <p className="text-xs text-slate-500">
                  {form.max_session_duration_minutes === 0
                    ? "No limit"
                    : `${form.max_session_duration_minutes} minutes`}
                </p>
              </div>
              <Slider
                className="w-[160px]"
                min={0}
                max={480}
                step={15}
                value={[form.max_session_duration_minutes]}
                onValueChange={(v) =>
                  update("max_session_duration_minutes", v[0])
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm text-slate-300">
                  Disable custom instructions
                </Label>
                <p className="text-xs text-slate-500">
                  Prevent modifying system prompts
                </p>
              </div>
              <Switch
                checked={form.disable_custom_instructions}
                onCheckedChange={(v) =>
                  update("disable_custom_instructions", v)
                }
              />
            </div>

            {/* The following div is replaced as per user instruction */}
            <div key="activity_log" className="flex items-center justify-between">
              <div>
                <Label className="text-sm text-slate-300">Activity log</Label>
                <p className="text-xs text-slate-500">Log all conversations for review</p>
              </div>
              <Switch
                checked={form.activity_log}
                onCheckedChange={(v) => update("activity_log", v)}
              />
            </div>

            {/* Allowed Models */}
            <div className="space-y-2">
              <Label className="text-sm text-slate-300">
                Allowed Models (empty = all)
              </Label>
              <div className="flex gap-2">
                <Input
                  className="bg-slate-900 border-slate-700 flex-1"
                  placeholder="e.g. llama3:8b"
                  value={modelInput}
                  onChange={(e) => setModelInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addModel()}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  className="bg-slate-800"
                  onClick={addModel}
                >
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {form.allowed_models.map((model: string) => (
                  <span
                    key={model}
                    className="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs cursor-pointer hover:bg-red-900/30 hover:text-red-400 transition-colors"
                    onClick={() => removeModel(model)}
                  >
                    {model} ×
                  </span>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      <Button
        onClick={() => onSave(form)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        <Save className="h-4 w-4 mr-2" />
        Save Parental Controls
      </Button>
    </div>
  );
}