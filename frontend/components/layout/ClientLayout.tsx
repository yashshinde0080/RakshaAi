'use client';

import { useStore } from '@/store';
import { SettingsDialog } from '@/components/settings/SettingsDialog';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const { settingsOpen, setSettingsOpen } = useStore();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
