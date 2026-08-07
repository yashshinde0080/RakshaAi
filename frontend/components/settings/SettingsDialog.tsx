"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  Settings,
  Bot,
  Palette,
  Database,
  Shield,
  Baby,
  RotateCcw,
  Info,
} from "lucide-react";
import { GeneralSettings } from "./GeneralSettings";
import { ProjectSettings } from "./ProjectSettings";
import { AgentSettings } from "./AgentSettings";

import { PersonalizationSettings } from "./PersonalizationSettings";
import { DataControlsSettings } from "./DataControlsSettings";
import { SecuritySettings } from "./SecuritySettings";
import { ParentalControlsSettings } from "./ParentalControlsSettings";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import type { Agent, SettingsMap } from "@/types";

type Section =
  | "general"
  | "project"
  | "agents"
  | "personalization"
  | "data_controls"
  | "security"
  | "parental_controls";


const EMPTY: Record<string, unknown> = {};

const sections: { key: Section; label: string; icon: React.ElementType }[] = [
  { key: "general", label: "General", icon: Settings },
  { key: "project", label: "Project Info", icon: Info },
  { key: "agents", label: "Agents", icon: Bot },
  { key: "personalization", label: "Personalization", icon: Palette },
  { key: "data_controls", label: "Data Controls", icon: Database },
  { key: "security", label: "Security", icon: Shield },
  { key: "parental_controls", label: "Parental Controls", icon: Baby },
];


interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [activeSection, setActiveSection] = useState<Section>("general");
  const [settings, setSettings] = useState<SettingsMap>({});
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchAllSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getAllSettings();
      const { agents: agentList, ...rest } = data;
      setSettings(rest);
      setAgents(agentList || []);
    } catch {
      toast({
        title: "Error",
        description: "Failed to load settings",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (open) {
      fetchAllSettings();
    }
  }, [open, fetchAllSettings]);

  const updateSection = async (section: string, data: Record<string, unknown>) => {
    try {
      const result = await api.updateSettingsSection(section, data);

      setSettings((prev) => ({ ...prev, [section]: data }));

      toast({
        title: "Saved",
        description: result.message || "Settings updated successfully",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to save settings",
        variant: "destructive",
      });
    }
  };

  const resetAll = async () => {
    try {
      await api.resetSettings();
      await fetchAllSettings();
      toast({ title: "Reset", description: "All settings restored to defaults" });
    } catch {
      toast({
        title: "Error",
        description: "Failed to reset settings",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-[900px] h-[80vh] max-h-[680px] p-0 bg-slate-950 border-slate-800 text-white overflow-hidden flex flex-col sm:flex-row">
        <div className="flex h-full w-full">
          {/* Sidebar */}
          <div className="w-[220px] shrink-0 border-r border-slate-800 flex flex-col">
            <DialogHeader className="p-4 pb-2">
              <DialogTitle className="text-lg font-semibold flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-500" />
                Settings
              </DialogTitle>
            </DialogHeader>
            <Separator className="bg-slate-800" />
            <ScrollArea className="flex-1 py-2">
              <nav className="flex flex-col gap-1 px-2">
                {sections.map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveSection(key)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left w-full",
                      activeSection === key
                        ? "bg-slate-800 text-white"
                        : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {label}
                  </button>
                ))}
              </nav>
            </ScrollArea>
            <Separator className="bg-slate-800" />
            <div className="p-3">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-slate-400 hover:text-red-400 hover:bg-red-950/20 justify-start gap-2"
                onClick={resetAll}
              >
                <RotateCcw className="h-4 w-4" />
                Reset All Defaults
              </Button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-6 py-4 pr-12 border-b border-slate-800 shrink-0">
              <h2 className="text-lg font-semibold capitalize">
                {sections.find((s) => s.key === activeSection)?.label}
              </h2>
            </div>
            <ScrollArea className="flex-1 px-6 py-4">
              {loading ? (
                <div className="flex items-center justify-center h-full text-slate-500">
                  Loading settings...
                </div>
              ) : (
                <>
                  {activeSection === "general" && (
                    <GeneralSettings
                      data={settings.general ?? EMPTY}
                      onSave={(data) => updateSection("general", data)}
                    />
                  )}
                  {activeSection === "project" && (
                    <ProjectSettings
                      data={settings.project ?? EMPTY}
                      onSave={(data) => updateSection("project", data)}
                    />
                  )}

                  {activeSection === "agents" && (
                    <AgentSettings
                      agents={agents}
                      onRefresh={fetchAllSettings}
                    />
                  )}
                  {activeSection === "personalization" && (
                    <PersonalizationSettings
                      data={settings.personalization ?? EMPTY}
                      onSave={(data) => updateSection("personalization", data)}
                    />
                  )}
                  {activeSection === "data_controls" && (
                    <DataControlsSettings
                      data={settings.data_controls ?? EMPTY}
                      onSave={(data) => updateSection("data_controls", data)}
                    />
                  )}
                  {activeSection === "security" && (
                    <SecuritySettings
                      data={settings.security ?? EMPTY}
                      onSave={(data) => updateSection("security", data)}
                    />
                  )}
                  {activeSection === "parental_controls" && (
                    <ParentalControlsSettings
                      data={settings.parental_controls ?? EMPTY}
                      onSave={(data) =>
                        updateSection("parental_controls", data)
                      }
                    />
                  )}
                </>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}