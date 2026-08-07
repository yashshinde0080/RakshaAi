// In your TopBar.tsx or layout component
import { SettingsIcon } from "@/components/settings/SettingsIcon";

export function TopBar() {
  return (
    <header className="h-12 border-b border-slate-800 bg-slate-950 flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-white">SovereignAI Edge</span>
      </div>
      <div className="flex items-center gap-2">
        {/* Other buttons */}
        <SettingsIcon />
      </div>
    </header>
  );
}