import { useColorScheme } from 'react-native';

export const colors = {
  light: {
    background: '#F4F6F8',
    surface: '#FFFFFF',
    text: '#101828',
    textSecondary: '#5D6B82',
    border: '#E2E8F0',
    accent: '#2563EB',
    accentPressed: '#1D4ED8',
    danger: '#DC2626',
    dangerPressed: '#B91C1C',
    switchTrackOn: '#2563EB',
    chipActiveBg: '#2563EB',
    chipActiveText: '#FFFFFF',
    chipInactiveBg: '#EEF2F7',
    chipInactiveText: '#334155',
    inputBg: '#F9FAFB',
  },
  dark: {
    background: '#0B1220',
    surface: '#151E2E',
    text: '#F1F5F9',
    textSecondary: '#94A3B8',
    border: '#243041',
    accent: '#3B82F6',
    accentPressed: '#2563EB',
    danger: '#EF4444',
    dangerPressed: '#DC2626',
    switchTrackOn: '#3B82F6',
    chipActiveBg: '#3B82F6',
    chipActiveText: '#FFFFFF',
    chipInactiveBg: '#1E293B',
    chipInactiveText: '#CBD5E1',
    inputBg: '#0F172A',
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
} as const;

export function useThemeColors() {
  const scheme = useColorScheme();
  return scheme === 'dark' ? colors.dark : colors.light;
}
