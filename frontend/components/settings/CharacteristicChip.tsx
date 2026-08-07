"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface CharacteristicChipProps {
  label: string;
  selected: boolean;
  onClick: () => void;
}

export function CharacteristicChip({
  label,
  selected,
  onClick,
}: CharacteristicChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-1.5 rounded-full text-sm font-medium transition-all border",
        selected
          ? "bg-blue-600/20 text-blue-400 border-blue-500/50"
          : "bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-500 hover:text-slate-300"
      )}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </button>
  );
}