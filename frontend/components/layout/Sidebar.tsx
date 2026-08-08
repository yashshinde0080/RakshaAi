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
  Home,
  HeartPulse
} from 'lucide-react';
import { BrandMark } from '@/components/BrandMark';
import { useStore } from '@/store';

const navItems = [
  { href: '/', icon: Home, label: 'Home' },
  { href: '/console', icon: MessageSquare, label: 'Console' },
  { href: '/triage', icon: HeartPulse, label: 'Triage' },
  { href: '/models', icon: Box, label: 'Models' },
  { href: '/documents', icon: FileText, label: 'Documents' },
  { href: '/system', icon: Activity, label: 'System' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { setSettingsOpen } = useStore();

  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b flex items-center gap-3">
        <BrandMark size={36} />
        <div>
          <h1 className="text-xl font-bold text-primary tracking-tight">Raksha AI</h1>
          <p className="text-xs text-muted-foreground">Offline Guardian</p>
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
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">Raksha AI</p>
          <p className="text-[10px] text-muted-foreground">v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}