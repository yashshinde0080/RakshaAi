"use client";

import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Save, Lock, AlertTriangle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

interface SecuritySettingsProps {
  data: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

export function SecuritySettings({ data, onSave }: SecuritySettingsProps) {
  const [form, setForm] = useState({
    require_password: false,
    encrypt_models: true,
    bind_localhost_only: true,
    api_port: 8000,
    enable_cors: false,
    allowed_origins: ["http://localhost:3000"],
    session_timeout_minutes: 0,
    audit_logging: true,
    disable_external_plugins: true,
    max_concurrent_requests: 4,
    ...data,
  });

  const [newPassword, setNewPassword] = useState("");
  const [originsInput, setOriginsInput] = useState("");
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

  const handleSetPassword = async () => {
    if (newPassword.length < 6) {
      toast({
        title: "Error",
        description: "Password must be at least 6 characters",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.setSecurityPassword(newPassword);
      toast({ title: "Password Set", description: "Application password has been set" });
      setNewPassword("");
      update("require_password", true);
    } catch {
      toast({
        title: "Error",
        description: "Failed to set password",
        variant: "destructive",
      });
    }
  };

  const addOrigin = () => {
    if (originsInput.trim() && !form.allowed_origins.includes(originsInput.trim())) {
      update("allowed_origins", [...form.allowed_origins, originsInput.trim()]);
      setOriginsInput("");
    }
  };

  const removeOrigin = (origin: string) => {
    update(
      "allowed_origins",
      form.allowed_origins.filter((o: string) => o !== origin)
    );
  };

  return (
    <div className="space-y-6">
      {/* Authentication */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Authentication
        </h3>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Require password</Label>
            <p className="text-xs text-slate-500">
              Protect app access with a password
            </p>
          </div>
          <Switch
            checked={form.require_password}
            onCheckedChange={(v) => update("require_password", v)}
          />
        </div>

        {form.require_password && (
          <div className="flex gap-2">
            <Input
              type="password"
              className="bg-slate-900 border-slate-700 flex-1"
              placeholder="Set new password (min 6 characters)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <Button
              variant="secondary"
              size="sm"
              className="bg-slate-800"
              onClick={handleSetPassword}
            >
              <Lock className="h-4 w-4 mr-1" />
              Set
            </Button>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">
              Session timeout (minutes)
            </Label>
            <p className="text-xs text-slate-500">
              {form.session_timeout_minutes === 0
                ? "No timeout"
                : `${form.session_timeout_minutes} minutes`}
            </p>
          </div>
          <Slider
            className="w-[160px]"
            min={0}
            max={120}
            step={5}
            value={[form.session_timeout_minutes]}
            onValueChange={(v) => update("session_timeout_minutes", v[0])}
          />
        </div>
      </div>

      {/* Network */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Network
        </h3>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">
              Bind to localhost only
            </Label>
            <p className="text-xs text-slate-500">
              Only allow local connections (127.0.0.1)
            </p>
          </div>
          <Switch
            checked={form.bind_localhost_only}
            onCheckedChange={(v) => update("bind_localhost_only", v)}
          />
        </div>

        {!form.bind_localhost_only && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-950/20 border border-red-500/20">
            <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            <p className="text-xs text-red-400">
              Warning: Disabling localhost-only binding exposes the API to your
              network. Only do this if you understand the security implications.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <Label className="text-sm text-slate-300">API Port</Label>
          <Input
            type="number"
            className="w-[120px] bg-slate-900 border-slate-700"
            min={1024}
            max={65535}
            value={form.api_port}
            onChange={(e) =>
              update("api_port", parseInt(e.target.value) || 8000)
            }
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm text-slate-300">Enable CORS</Label>
            <p className="text-xs text-slate-500">
              Allow cross-origin requests
            </p>
          </div>
          <Switch
            checked={form.enable_cors}
            onCheckedChange={(v) => update("enable_cors", v)}
          />
        </div>

        {form.enable_cors && (
          <div className="space-y-2">
            <Label className="text-sm text-slate-300">Allowed Origins</Label>
            <div className="flex gap-2">
              <Input
                className="bg-slate-900 border-slate-700 flex-1"
                placeholder="http://localhost:3000"
                value={originsInput}
                onChange={(e) => setOriginsInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addOrigin()}
              />
              <Button
                variant="secondary"
                size="sm"
                className="bg-slate-800"
                onClick={addOrigin}
              >
                Add
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {form.allowed_origins.map((origin: string) => (
                <span
                  key={origin}
                  className="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs cursor-pointer hover:bg-red-900/30 hover:text-red-400 transition-colors"
                  onClick={() => removeOrigin(origin)}
                >
                  {origin} ×
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Protection */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Protection
        </h3>

        {[
          {
            key: "encrypt_models",
            label: "Encrypt models at rest",
            desc: "AES-256 encryption for model files",
          },
          {
            key: "audit_logging",
            label: "Audit logging",
            desc: "Log all settings changes and actions",
          },
          {
            key: "disable_external_plugins",
            label: "Disable external plugins",
            desc: "Only allow built-in plugins",
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
            <Label className="text-sm text-slate-300">
              Max concurrent requests
            </Label>
            <p className="text-xs text-slate-500">
              {form.max_concurrent_requests} simultaneous requests
            </p>
          </div>
          <Slider
            className="w-[160px]"
            min={1}
            max={32}
            step={1}
            value={[form.max_concurrent_requests]}
            onValueChange={(v) => update("max_concurrent_requests", v[0])}
          />
        </div>
      </div>

      <Button
        onClick={() => onSave(form)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        <Save className="h-4 w-4 mr-2" />
        Save Security Settings
      </Button>
    </div>
  );
}