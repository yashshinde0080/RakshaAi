"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Bot,
  Stethoscope,
  Code,
  Scale,
  GraduationCap,
  FlaskConical,
  PenTool,

  Heart,
  DollarSign,
  BarChart,
  Shield,
  ChefHat,
  Dumbbell,
  Megaphone,
  BookOpen,
  Brain,
  Power,
  Pencil,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
  bot: Bot,
  stethoscope: Stethoscope,
  code: Code,
  scale: Scale,
  "graduation-cap": GraduationCap,
  "flask-conical": FlaskConical,
  "pen-tool": PenTool,


  heart: Heart,
  "dollar-sign": DollarSign,
  "bar-chart": BarChart,
  shield: Shield,
  "chef-hat": ChefHat,
  dumbbell: Dumbbell,
  megaphone: Megaphone,
  book: BookOpen,
  brain: Brain,
};

interface AgentCardProps {
  agent: {
    id: string;
    name: string;
    role: string;
    description: string;
    is_active: boolean;
    icon: string;
    temperature: number;
    max_tokens: number;
    enabled: boolean;
  };
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function AgentCard({
  agent,
  onActivate,
  onEdit,
  onDelete,
}: AgentCardProps) {
  const IconComponent = ICON_MAP[agent.icon] || Bot;

  return (
    <Card
      className={cn(
        "p-4 border transition-colors",
        agent.is_active
          ? "bg-blue-950/20 border-blue-500/40"
          : "bg-slate-900 border-slate-800 hover:border-slate-700"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
              agent.is_active ? "bg-blue-600/20" : "bg-slate-800"
            )}
          >
            <IconComponent
              className={cn(
                "h-5 w-5",
                agent.is_active ? "text-blue-400" : "text-slate-400"
              )}
            />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-white truncate">
                {agent.name}
              </h4>
              {agent.is_active && (
                <Badge className="bg-blue-600/20 text-blue-400 text-[10px] px-1.5 py-0">
                  Active
                </Badge>
              )}
              {!agent.enabled && (
                <Badge
                  variant="secondary"
                  className="bg-slate-800 text-slate-500 text-[10px] px-1.5 py-0"
                >
                  Disabled
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 capitalize">
              {agent.role.replace(/_/g, " ")}
            </p>
            {agent.description && (
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                {agent.description}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-500">
              <span>Temp: {agent.temperature}</span>
              <span>Max: {agent.max_tokens.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0 ml-2">
          {!agent.is_active && agent.enabled && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-slate-400 hover:text-green-400"
              onClick={onActivate}
              title="Activate"
            >
              <Power className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-400 hover:text-white"
            onClick={onEdit}
            title="Edit"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-400 hover:text-red-400"
            onClick={onDelete}
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}