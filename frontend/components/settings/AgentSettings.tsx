"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, PowerOff } from "lucide-react";

import { AgentCard } from "./AgentCard";

import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import type { Agent } from "@/types";

const ROLES = [
  { value: "doctor", label: "Doctor" },
  { value: "engineer", label: "Engineer" },
  { value: "lawyer", label: "Lawyer" },
  { value: "teacher", label: "Teacher" },
  { value: "scientist", label: "Scientist" },
  { value: "writer", label: "Writer" },
  { value: "therapist", label: "Therapist" },
  { value: "financial_advisor", label: "Financial Advisor" },
  { value: "chef", label: "Chef" },
  { value: "fitness_trainer", label: "Fitness Trainer" },
  { value: "data_analyst", label: "Data Analyst" },
  { value: "marketing_expert", label: "Marketing Expert" },
  { value: "cybersecurity_expert", label: "Cybersecurity Expert" },
  { value: "historian", label: "Historian" },
  { value: "philosopher", label: "Philosopher" },
  { value: "custom", label: "Custom" },
];

const ICONS = [
  "bot",
  "stethoscope",
  "code",
  "scale",
  "graduation-cap",
  "flask",
  "flask-conical",
  "pen-tool",

  "heart",
  "dollar-sign",
  "bar-chart",
  "shield",
  "chef-hat",
  "dumbbell",
  "megaphone",
  "book",
  "brain",
];

interface AgentSettingsProps {
  agents: Agent[];
  onRefresh: () => void;
}

export function AgentSettings({ agents, onRefresh }: AgentSettingsProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const { toast } = useToast();

  const [form, setForm] = useState({
    id: "",
    name: "",
    role: "custom",
    description: "",
    system_instruction: "",
    is_active: false,
    icon: "bot",
    temperature: 0.7,
    max_tokens: 2048,
    enabled: true,
  });

  const resetForm = () => {
    setForm({
      id: "",
      name: "",
      role: "custom",
      description: "",
      system_instruction: "",
      is_active: false,
      icon: "bot",
      temperature: 0.7,
      max_tokens: 2048,
      enabled: true,
    });
  };

  const updateForm = (key: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [key]: value }) as typeof form);
  };

  const handleCreate = async () => {
    const agentId = `agent_${form.name.toLowerCase().replace(/\s+/g, "_")}_${Date.now()}`;
    const payload = { ...form, id: agentId };

    try {
      await api.createAgent(payload);
      toast({ title: "Created", description: `Agent '${form.name}' created` });
      setCreateOpen(false);
      resetForm();
      onRefresh();
    } catch {
      toast({
        title: "Error",
        description: "Failed to create agent",
        variant: "destructive",
      });
    }
  };

  const handleUpdate = async () => {
    if (!editAgent) return;
    try {
      await api.updateAgent(editAgent.id, form);
      toast({ title: "Updated", description: "Agent updated" });
      setEditAgent(null);
      resetForm();
      onRefresh();
    } catch {
      toast({
        title: "Error",
        description: "Failed to update agent",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (agentId: string) => {
    try {
      await api.deleteAgent(agentId);
      toast({ title: "Deleted", description: "Agent removed" });
      onRefresh();
    } catch {
      toast({
        title: "Error",
        description: "Failed to delete agent",
        variant: "destructive",
      });
    }
  };

  const handleActivate = async (agentId: string) => {
    try {
      await api.activateAgent(agentId);
      toast({ title: "Activated", description: "Agent activated" });
      onRefresh();
    } catch {
      toast({
        title: "Error",
        description: "Failed to activate agent",
        variant: "destructive",
      });
    }
  };

  const handleDeactivateAll = async () => {
    try {
      await api.deactivateAllAgents();
      toast({ title: "Deactivated", description: "All agents deactivated" });
      onRefresh();
    } catch {
      toast({
        title: "Error",
        description: "Failed to deactivate",
        variant: "destructive",
      });
    }
  };

  const openEdit = (agent: Agent) => {
    setForm({ ...agent });
    setEditAgent(agent);
  };

  const agentFormDialog = (
    isEdit: boolean,
    open: boolean,
    onClose: () => void
  ) => (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-slate-950 border-slate-800 text-white max-w-[600px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit Agent" : "Create New Agent"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="text-sm text-slate-300">Name</Label>
            <Input
              className="bg-slate-900 border-slate-700"
              placeholder="Agent name"
              value={form.name}
              onChange={(e) => updateForm("name", e.target.value)}
            />
          </div>

          <div className="flex gap-4">
            <div className="flex-1 space-y-2">
              <Label className="text-sm text-slate-300">Role</Label>
              <Select
                value={form.role}
                onValueChange={(v) => updateForm("role", v)}
              >
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700">
                  {ROLES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 space-y-2">
              <Label className="text-sm text-slate-300">Icon</Label>
              <Select
                value={form.icon}
                onValueChange={(v) => updateForm("icon", v)}
              >
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700">
                  {ICONS.map((i) => (
                    <SelectItem key={i} value={i}>
                      {i}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm text-slate-300">Description</Label>
            <Textarea
              className="bg-slate-900 border-slate-700 min-h-[60px]"
              placeholder="Brief description of this agent's purpose"
              value={form.description}
              onChange={(e) => updateForm("description", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm text-slate-300">
              System Instruction (Role Prompt)
            </Label>
            <Textarea
              className="bg-slate-900 border-slate-700 min-h-[200px] font-mono text-sm"
              placeholder="Define the agent's behavior, expertise, constraints, and personality..."
              value={form.system_instruction}
              onChange={(e) =>
                updateForm("system_instruction", e.target.value)
              }
            />
          </div>

          <div className="flex gap-4">
            <div className="flex-1 space-y-2">
              <Label className="text-sm text-slate-300">
                Temperature: {form.temperature}
              </Label>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={[form.temperature]}
                onValueChange={(v) => updateForm("temperature", v[0])}
              />
              <p className="text-xs text-slate-500">
                Lower = more focused. Higher = more creative.
              </p>
            </div>

            <div className="flex-1 space-y-2">
              <Label className="text-sm text-slate-300">Max Tokens</Label>
              <Input
                type="number"
                className="bg-slate-900 border-slate-700"
                min={64}
                max={32768}
                step={256}
                value={form.max_tokens}
                onChange={(e) =>
                  updateForm("max_tokens", parseInt(e.target.value) || 2048)
                }
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-sm text-slate-300">Enabled</Label>
            <Switch
              checked={form.enabled}
              onCheckedChange={(v) => updateForm("enabled", v)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            className="bg-blue-600 hover:bg-blue-700"
            onClick={isEdit ? handleUpdate : handleCreate}
            disabled={!form.name.trim()}
          >
            {isEdit ? "Update Agent" : "Create Agent"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="space-y-6 pb-6">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            AI Agents
          </h3>
          <p className="text-xs text-slate-500 mt-1 sm:max-w-md">
            Configure specialized AI agents with specific roles and
            instructions.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
            onClick={handleDeactivateAll}
          >
            <PowerOff className="h-4 w-4 mr-1" />
            Deactivate All
          </Button>
          <Button
            size="sm"
            className="bg-blue-600 hover:bg-blue-700"
            onClick={() => {
              resetForm();
              setCreateOpen(true);
            }}
          >
            <Plus className="h-4 w-4 mr-1" />
            New Agent
          </Button>
        </div>
      </div>

      <div className="grid gap-3">
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onActivate={() => handleActivate(agent.id)}
            onEdit={() => openEdit(agent)}
            onDelete={() => handleDelete(agent.id)}
          />
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          No agents configured. Create your first agent.
        </div>
      )}

      {/* Create Dialog */}
      {agentFormDialog(false, createOpen, () => setCreateOpen(false))}

      {/* Edit Dialog */}
      {agentFormDialog(true, !!editAgent, () => {
        setEditAgent(null);
        resetForm();
      })}
    </div>
  );
}