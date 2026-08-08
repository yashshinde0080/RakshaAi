import React from 'react';
import { Tabs, useRouter, usePathname } from 'expo-router';
import { Pressable, View, StyleSheet } from 'react-native';

import { ThemedText } from './themed-text';
import { Icon } from './icons';
import { BrandLockup, BrandMark } from './brand';
import { useServer } from '@/hooks/useServer';

const NAV_ITEMS = [
  { name: 'index', href: '/', label: 'Home', icon: 'home' },
  { name: 'console', href: '/console', label: 'Console', icon: 'console' },
  { name: 'models', href: '/models', label: 'Models', icon: 'models' },
  { name: 'documents', href: '/documents', label: 'Documents', icon: 'documents' },
  { name: 'benchmark', href: '/benchmark', label: 'Benchmark', icon: 'benchmark' },
  { name: 'system', href: '/system', label: 'System', icon: 'system' },
  { name: 'workspace', href: '/workspace', label: 'Workspace', icon: 'workspace' },
  { name: 'plugins', href: '/plugins', label: 'Plugins', icon: 'plugins' },
] as const;

export default function AppTabs() {
  const { status } = useServer();
  const pathname = usePathname();
  const router = useRouter();

  const activeModel = status?.model_loaded && status.current_model
    ? status.current_model
    : 'tdh111/bitnet-b1.58-2B-4T-GGUF';
  const activeMode = status?.current_mode ?? 'fullram';

  const ramUsed = status?.ram_used_gb ? status.ram_used_gb.toFixed(1) : '7.4';
  const ramPercent = status?.ram_total_gb
    ? Math.round((status.ram_used_gb / status.ram_total_gb) * 100)
    : 77;

  return (
    <View style={styles.webWrapper}>
      {/* Raksha AI Sidebar */}
      <View style={styles.sidebar}>
        {/* Brand Header */}
        <View style={styles.brandHeader}>
          <BrandLockup title="RAKSHA AI" subtitle="Offline Guardian" size={38} />
        </View>

        {/* Navigation List */}
        <View style={styles.tabListContainer}>
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));

            return (
              <Pressable
                key={item.name}
                onPress={() => router.push(item.href)}
                style={({ pressed }) => [
                  styles.navButton,
                  active && styles.navButtonActive,
                  pressed && styles.pressed,
                ]}
              >
                <Icon name={item.icon} size={18} color={active ? '#ffffff' : '#7fa094'} />
                <ThemedText style={[styles.navText, active && styles.navTextActive]}>
                  {item.label}
                </ThemedText>
              </Pressable>
            );
          })}
        </View>

        {/* Bottom Sidebar Actions & Profile */}
        <View style={styles.sidebarFooter}>
          <Pressable
            onPress={() => router.push('/settings')}
            style={({ pressed }) => [
              styles.navButton,
              pathname === '/settings' && styles.navButtonActive,
              pressed && styles.pressed,
            ]}
          >
            <Icon name="settings" size={18} color={pathname === '/settings' ? '#ffffff' : '#7fa094'} />
            <ThemedText style={[styles.navText, pathname === '/settings' && styles.navTextActive]}>
              Settings
            </ThemedText>
          </Pressable>

          <View style={styles.profileBadge}>
            <View style={styles.profileAvatar}>
              <BrandMark size={20} />
            </View>
            <View style={styles.profileInfo}>
              <ThemedText style={styles.profileTitle}>RAKSHA AI</ThemedText>
              <ThemedText style={styles.profileVersion}>v1.0.0 · offline-first</ThemedText>
            </View>
          </View>
        </View>
      </View>

      {/* Main Container */}
      <View style={styles.mainContainer}>
        {/* Top Status Header */}
        <View style={styles.headerBar}>
          <View style={styles.headerStatusLeft}>
            <View style={styles.statusDotActive} />
            <ThemedText style={styles.headerModelText}>
              {activeModel} <ThemedText style={styles.headerModeTag}>| {activeMode}</ThemedText>
            </ThemedText>
          </View>

          <View style={styles.headerMetricsRight}>
            <View style={styles.metricBadge}>
              <Icon name="activity" size={14} color="#7fa094" />
              <ThemedText style={styles.metricText}>{ramPercent}%</ThemedText>
            </View>

            <View style={styles.metricBadge}>
              <Icon name="ram" size={14} color="#7fa094" />
              <ThemedText style={styles.metricText}>{ramUsed} GB</ThemedText>
            </View>

            <View style={styles.connectedBadge}>
              <View style={styles.connectedDot} />
              <ThemedText style={styles.connectedText}>Connected</ThemedText>
            </View>
          </View>
        </View>

        {/* Tab Navigator Screen Content */}
        <View style={styles.slotContainer}>
          <Tabs
            screenOptions={{
              headerShown: false,
              tabBarStyle: { display: 'none' },
            }}
          >
            <Tabs.Screen name="index" />
            <Tabs.Screen name="console" />
            <Tabs.Screen name="models" />
            <Tabs.Screen name="documents" />
            <Tabs.Screen name="benchmark" />
            <Tabs.Screen name="system" />
            <Tabs.Screen name="workspace" />
            <Tabs.Screen name="plugins" />
            <Tabs.Screen name="settings" />
            <Tabs.Screen name="chat" />
          </Tabs>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  webWrapper: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#04100d',
    height: '100%',
    width: '100%',
    overflow: 'hidden',
  },
  sidebar: {
    width: 240,
    backgroundColor: '#071612',
    borderRightWidth: 1,
    borderRightColor: '#1a352c',
    paddingVertical: 20,
    paddingHorizontal: 16,
    justifyContent: 'space-between',
  },
  brandHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 24,
    paddingHorizontal: 4,
  },
  tabListContainer: {
    flex: 1,
    gap: 4,
  },
  navButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: 'transparent',
  },
  navButtonActive: {
    backgroundColor: '#14b8a6',
  },
  navText: {
    color: '#7fa094',
    fontSize: 14,
    fontWeight: '500',
  },
  navTextActive: {
    color: '#ffffff',
    fontWeight: '600',
  },
  sidebarFooter: {
    gap: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#1a352c',
  },
  profileBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 4,
  },
  profileAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#1a352c',
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileInfo: {
    justifyContent: 'center',
  },
  profileTitle: {
    color: '#7fa094',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  profileVersion: {
    color: '#4d6b60',
    fontSize: 11,
  },
  mainContainer: {
    flex: 1,
    backgroundColor: '#04100d',
    flexDirection: 'column',
  },
  headerBar: {
    height: 52,
    borderBottomWidth: 1,
    borderBottomColor: '#1a352c',
    paddingHorizontal: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#04100d',
  },
  headerStatusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  statusDotActive: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
  },
  headerModelText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '600',
    fontFamily: 'var(--font-mono)',
  },
  headerModeTag: {
    color: '#7fa094',
    fontWeight: '400',
  },
  headerMetricsRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  metricBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metricText: {
    color: '#7fa094',
    fontSize: 13,
    fontWeight: '500',
  },
  connectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#0b1a15',
    borderWidth: 1,
    borderColor: '#1a352c',
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  connectedDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10b981',
  },
  connectedText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '500',
  },
  slotContainer: {
    flex: 1,
    overflow: 'hidden',
  },
  pressed: {
    opacity: 0.7,
  },
});
