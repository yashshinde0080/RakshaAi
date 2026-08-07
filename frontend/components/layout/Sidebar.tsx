'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  MessageSquare,
  Box,
  Settings,
  Activity,
  FileText,
  Puzzle,
  Home,
  Gauge,
  Save
} from 'lucide-react';
import { useStore } from '@/store';

const navItems = [
  { href: '/', icon: Home, label: 'Home' },
  { href: '/console', icon: MessageSquare, label: 'Console' },
  { href: '/models', icon: Box, label: 'Models' },
  { href: '/documents', icon: FileText, label: 'Documents' },
  { href: '/benchmark', icon: Gauge, label: 'Benchmark' },
  { href: '/system', icon: Activity, label: 'System' },
  { href: '/workspace', icon: Save, label: 'Workspace' },
  { href: '/plugins', icon: Puzzle, label: 'Plugins' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { setSettingsOpen } = useStore();

  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b flex items-center gap-3">
        <div
          aria-hidden="true"
          className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand to-brand-accent flex items-center justify-center text-white text-sm font-bold shrink-0"
        >
          S
        </div>
        <div>
          <h1 className="text-xl font-bold text-primary">SovereignAI</h1>
          <p className="text-xs text-muted-foreground">Edge Platform</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground dark:bg-brand dark:text-white'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t space-y-2">
        <button
          onClick={() => setSettingsOpen(true)}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors w-full text-muted-foreground hover:text-foreground hover:bg-muted"
        >
          <Settings className="h-4 w-4" />
          Settings
        </button>
        <div className="flex items-center justify-between px-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">SovereignAI</p>
          <p className="text-[10px] text-muted-foreground">v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}