// Raksha AI brand mark — a protective shield with an ECG pulse. The
// heartbeat line is the identity motif across splash, sidebar and home.
//
// Platform split (same convention as icons.tsx): web renders the SVG shield;
// native renders a pure-View monogram tile — no react-native-svg dependency,
// so the offline native build never loads an extra native module.
import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

function WebMark({ size, light }: { size: number; light?: boolean }) {
  const line = light ? '#04100d' : '#e9f5f0';
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <defs>
        <linearGradient id="raksha-shield" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#0d9488" />
          <stop offset="1" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <path
        d="M24 3.2l15.6 5.8v11.4c0 9.3-6.3 16.4-15.6 21.8C14.7 36.8 8.4 29.7 8.4 20.4V9L24 3.2z"
        fill="url(#raksha-shield)"
        stroke="#2dd4bf"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 24.5h5.2l2.2-4.6 3.4 8.6 2.4-6.2 1.9 3 1.9-0.8h6"
        stroke={line}
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M15 27.8h18" stroke={line} strokeWidth="1.4" strokeOpacity="0.55" strokeLinecap="round" />
    </svg>
  );
}

function NativeMark({ size, light }: { size: number; light?: boolean }) {
  const line = light ? '#04100d' : '#e9f5f0';
  const tick = (h: number) => ({
    width: Math.max(2, size * 0.045),
    height: Math.max(2, h),
    borderRadius: size * 0.02,
    backgroundColor: line,
  });
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.3,
        backgroundColor: '#0d9488',
        borderWidth: 1,
        borderColor: '#2dd4bf',
        alignItems: 'center',
        justifyContent: 'center',
        gap: Math.max(2, size * 0.06),
      }}>
      <Text
        style={{
          color: '#e9f5f0',
          fontWeight: '800',
          fontSize: size * 0.42,
          lineHeight: size * 0.46,
        }}>
        R
      </Text>
      <View style={[styles.pulse, { height: Math.max(4, size * 0.16) }]}>
        <View style={tick(Math.max(3, size * 0.08))} />
        <View style={tick(Math.max(4, size * 0.16))} />
        <View style={tick(Math.max(3, size * 0.11))} />
      </View>
    </View>
  );
}

export function BrandMark({ size = 40, light = false }: { size?: number; light?: boolean }) {
  return Platform.OS === 'web' ? <WebMark size={size} light={light} /> : <NativeMark size={size} light={light} />;
}

export function BrandLockup({
  title = 'RAKSHA AI',
  subtitle = 'Offline Guardian',
  size = 38,
}: {
  title?: string;
  subtitle?: string;
  size?: number;
}) {
  return (
    <View style={styles.lockup}>
      <BrandMark size={size} />
      <View style={styles.lockupText}>
        <Text
          style={{
            color: '#e9f5f0',
            fontWeight: '700',
            fontSize: size * 0.42,
            lineHeight: size * 0.5,
            letterSpacing: size * 0.05,
          }}>
          {title}
        </Text>
        <Text style={[styles.lockupSubtitle, { fontSize: size * 0.3, lineHeight: size * 0.38 }]}>
          {subtitle}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  lockup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  lockupText: {
    justifyContent: 'center',
  },
  lockupSubtitle: {
    color: '#7fa094',
    letterSpacing: 0.6,
  },
  pulse: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 3,
  },
});
