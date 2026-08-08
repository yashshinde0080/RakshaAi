import '@/global.css';

import { Platform } from 'react-native';

// Raksha AI — "protection". A clinical-guardian palette: deep teal-black
// surfaces, protective teal accent, signal red reserved for emergencies.
export const Colors = {
  light: {
    text: '#0b1a15',
    background: '#f2f7f4',
    backgroundElement: '#e3ede8',
    backgroundSelected: '#14b8a6',
    textSecondary: '#5a7268',
    error: '#e11d48',
    border: '#d4e2dc',
    accent: '#0f766e',
  },
  dark: {
    text: '#e9f5f0',
    background: '#04100d',
    backgroundElement: '#0b1a15',
    backgroundSelected: '#14b8a6',
    textSecondary: '#7fa094',
    error: '#fb7185',
    border: '#1a352c',
    accent: '#2dd4bf',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 1400;
