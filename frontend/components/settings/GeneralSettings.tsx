"use client";

import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Save } from "lucide-react";

interface GeneralSettingsProps {
  data: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

export function GeneralSettings({ data, onSave }: GeneralSettingsProps) {
  const [form, setForm] = useState({
    theme: "dark",
    language: "en",
    auto_start_backend: true,
    minimize_to_tray: true,
    show_status_bar: true,
    enable_notifications: true,
    startup_model: "",
    default_mode: "auto",
    max_context_length: 4096,
    stream_responses: true,
    show_token_speed: true,
    font_size: 14,
    send_on_enter: true,
    enable_sounds: false,
    auto_save_sessions: true,
    ...data,
  });

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

  return (
    <div className="space-y-6">
      {/* Appearance */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Appearance
        </h3>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Theme</Label>
          <Select value={form.theme} onValueChange={(v) => update("theme", v)}>
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Language</Label>
          <Select
            value={form.language}
            onValueChange={(v) => update("language", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="es">Spanish</SelectItem>
              <SelectItem value="fr">French</SelectItem>
              <SelectItem value="de">German</SelectItem>
              <SelectItem value="ja">Japanese</SelectItem>
              <SelectItem value="zh">Chinese</SelectItem>
              <SelectItem value="hi">Hindi</SelectItem>
              <SelectItem value="ar">Arabic</SelectItem>
              <SelectItem value="pt">Portuguese</SelectItem>
              <SelectItem value="ru">Russian</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Font Size</Label>
            <p className="text-xs text-slate-500">{form.font_size}px</p>
          </div>
          <Slider
            className="w-[160px]"
            min={10}
            max={24}
            step={1}
            value={[form.font_size]}
            onValueChange={(v) => update("font_size", v[0])}
          />
        </div>
      </div>

      {/* Runtime */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Runtime
        </h3>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Default Mode</Label>
          <Select
            value={form.default_mode}
            onValueChange={(v) => update("default_mode", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              <SelectItem value="auto">Auto</SelectItem>
              <SelectItem value="fullram">Full RAM</SelectItem>
              <SelectItem value="layerstream">Layer Stream</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Max Context Length</Label>
            <p className="text-xs text-slate-500">
              {form.max_context_length.toLocaleString()} tokens
            </p>
          </div>
          <Input
            type="number"
            className="w-[160px] bg-slate-900 border-slate-700"
            min={512}
            max={131072}
            step={512}
            value={form.max_context_length}
            onChange={(e) =>
              update("max_context_length", parseInt(e.target.value) || 4096)
            }
          />
        </div>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Startup Model</Label>
          <Input
            className="w-[220px] bg-slate-900 border-slate-700"
            placeholder="e.g. llama3:8b"
            value={form.startup_model || ""}
            onChange={(e) => update("startup_model", e.target.value)}
          />
        </div>
      </div>

      {/* Behavior */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Behavior
        </h3>

        {[
          {
            key: "auto_start_backend",
            label: "Auto-start backend",
            desc: "Start inference server automatically",
          },
          {
            key: "minimize_to_tray",
            label: "Minimize to tray",
            desc: "Keep running in system tray",
          },
          {
            key: "show_status_bar",
            label: "Show status bar",
            desc: "Display model and system info",
          },
          {
            key: "enable_notifications",
            label: "Enable notifications",
            desc: "Desktop notifications for events",
          },
          {
            key: "stream_responses",
            label: "Stream responses",
            desc: "Show tokens as they generate",
          },
          {
            key: "show_token_speed",
            label: "Show token speed",
            desc: "Display tokens per second",
          },
          {
            key: "send_on_enter",
            label: "Send on Enter",
            desc: "Press Enter to send messages",
          },
          {
            key: "enable_sounds",
            label: "Enable sounds",
            desc: "Play audio feedback",
          },
          {
            key: "auto_save_sessions",
            label: "Auto-save sessions",
            desc: "Automatically save chat history",
          },
        ].map(({ key, label, desc }) => (
          <div key={key} className="flex items-center justify-between">
            <div>
              <Label className="text-sm text-slate-300">{label}</Label>
              <p className="text-xs text-slate-500">{desc}</p>
            </div>
            <Switch
              checked={form[key as keyof typeof form] as boolean}
              onCheckedChange={(v) => update(key, v)}
            />
          </div>
        ))}
      </div>

      <Button
        onClick={() => onSave(form)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        <Save className="h-4 w-4 mr-2" />
        Save General Settings
      </Button>
    </div>
  );
}