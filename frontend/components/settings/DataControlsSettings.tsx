"use client";

import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Save, AlertTriangle } from "lucide-react";

interface DataControlsSettingsProps {
  data: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

export function DataControlsSettings({
  data,
  onSave,
}: DataControlsSettingsProps) {
  const [form, setForm] = useState({
    save_chat_history: true,
    data_retention: "30_days",
    allow_model_training: false,
    export_format: "json",
    auto_delete_sessions: false,
    encrypt_local_data: true,
    log_api_requests: false,
    clear_on_exit: false,
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
      {/* Storage */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Data Storage
        </h3>

        {[
          {
            key: "save_chat_history",
            label: "Save chat history",
            desc: "Store conversation sessions locally",
          },
          {
            key: "encrypt_local_data",
            label: "Encrypt local data",
            desc: "AES-256 encryption for stored data",
          },
          {
            key: "auto_delete_sessions",
            label: "Auto-delete old sessions",
            desc: "Remove sessions based on retention policy",
          },
          {
            key: "clear_on_exit",
            label: "Clear data on exit",
            desc: "Delete all session data when app closes",
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

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Data Retention</Label>
            <p className="text-xs text-slate-500">
              How long to keep chat history
            </p>
          </div>
          <Select
            value={form.data_retention}
            onValueChange={(v) => update("data_retention", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              <SelectItem value="session_only">Session Only</SelectItem>
              <SelectItem value="1_day">1 Day</SelectItem>
              <SelectItem value="7_days">7 Days</SelectItem>
              <SelectItem value="30_days">30 Days</SelectItem>
              <SelectItem value="90_days">90 Days</SelectItem>
              <SelectItem value="indefinite">Indefinite</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Privacy */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Privacy
        </h3>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">
              Allow model training
            </Label>
            <p className="text-xs text-slate-500">
              Share data for model improvement (local only)
            </p>
          </div>
          <Switch
            checked={form.allow_model_training}
            onCheckedChange={(v) => update("allow_model_training", v)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Log API requests</Label>
            <p className="text-xs text-slate-500">
              Keep detailed request/response logs
            </p>
          </div>
          <Switch
            checked={form.log_api_requests}
            onCheckedChange={(v) => update("log_api_requests", v)}
          />
        </div>
      </div>

      {/* Export */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Export
        </h3>

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">Export Format</Label>
          <Select
            value={form.export_format}
            onValueChange={(v) => update("export_format", v)}
          >
            <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700">
              <SelectItem value="json">JSON</SelectItem>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="markdown">Markdown</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {form.clear_on_exit && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-950/20 border border-amber-500/20">
          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-400">
            Clear on exit is enabled. All session data will be permanently
            deleted when the application closes.
          </p>
        </div>
      )}

      <Button
        onClick={() => onSave(form)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        <Save className="h-4 w-4 mr-2" />
        Save Data Controls
      </Button>
    </div>
  );
}