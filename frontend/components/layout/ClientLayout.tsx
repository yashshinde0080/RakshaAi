'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/store';
import { SettingsDialog } from '@/components/settings/SettingsDialog';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { settingsOpen, setSettingsOpen } = useStore();

  // Electron shell menu/tray navigation (electron/menu.js + tray.js send a
  // 'navigate' IPC event; the preload exposes it as electronAPI.onNavigate).
  useEffect(() => {
    return window.electronAPI?.onNavigate?.((path) => router.push(path));
  }, [router]);

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
