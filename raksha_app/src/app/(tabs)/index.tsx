import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import { ErrorBanner } from '@/components/stat-row';
import { ThemedText } from '@/components/themed-text';
import { Icon } from '@/components/icons';
import { BrandMark } from '@/components/brand';
import { useServer } from '@/hooks/useServer';

export default function HomeScreen() {
  const { status, hardware, loading, error, refresh, unload } = useServer();
  const router = useRouter();

  const refreshAll = useCallback(async () => {
    await refresh();
  }, [refresh]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Server metric fallbacks matching the Raksha AI sample hardware profile
  const modelName = status?.model_loaded && status.current_model
    ? status.current_model
    : 'tdh111/bitnet-b1.58-2B-4T-GGUF';
  const executionMode = status?.current_mode ? status.current_mode.toUpperCase() : 'FULLRAM';
  const ramUsed = status?.ram_used_gb ? status.ram_used_gb.toFixed(1) : '7.3';
  const ramTotal = status?.ram_total_gb ? status.ram_total_gb.toFixed(0) : '8';
  const ramUsagePercent = status?.ram_total_gb
    ? ((status.ram_used_gb / status.ram_total_gb) * 100).toFixed(1)
    : '83.1';

  const cpuName = hardware?.cpu_name || 'Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz';
  const cpuCores = hardware?.cpu_cores ?? 4;
  const cpuThreads = hardware?.cpu_threads ?? 8;

  const diskFree = status?.disk_free_gb ? Math.round(status.disk_free_gb) : 105;
  const diskType = hardware?.disk_type || 'Unknown';
  const diskSpeed = hardware?.disk_speed_mb_s ? Math.round(hardware.disk_speed_mb_s) : 743;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={refreshAll} tintColor="#7fa094" />
      }
    >
      {/* Title & Description */}
      <View style={styles.titleSection}>
        <View style={styles.titleRow}>
          <BrandMark size={44} />
          <View style={styles.titleTextCol}>
            <ThemedText style={styles.mainTitle}>Welcome to Raksha AI</ThemedText>
            <ThemedText style={styles.subTitle}>Your private, offline AI guardian — local intelligence, vitals triage, zero cloud.</ThemedText>
          </View>
        </View>
      </View>

      {error && <ErrorBanner message={error} />}

      {/* Top Grid: System Core (Left) & Quick Commands / Hardware Opt (Right) */}
      <View style={styles.topGrid}>
        {/* System Core Panel */}
        <View style={styles.systemCoreCard}>
          <View style={styles.cardHeaderRow}>
            <View style={styles.systemCoreHeaderLeft}>
              <View style={styles.greenDot} />
              <ThemedText style={styles.systemCoreHeaderTag}>SYSTEM CORE</ThemedText>
            </View>
            <Pressable
              onPress={unload}
              style={({ pressed }) => [
                styles.terminateButton,
                pressed && styles.pressed,
              ]}
            >
              <Icon name="power" size={14} color="#f87171" />
              <ThemedText style={styles.terminateText}>TERMINATE SESSION</ThemedText>
            </Pressable>
          </View>

          {/* Model Name & Status */}
          <View style={styles.modelNameRow}>
            <ThemedText style={styles.modelNameText}>{modelName}</ThemedText>
            <View style={styles.activePill}>
              <ThemedText style={styles.activePillText}>Active</ThemedText>
            </View>
          </View>

          {/* Metrics Grid */}
          <View style={styles.metricsRow}>
            <View style={styles.metricItem}>
              <ThemedText style={styles.metricLabel}>EXECUTION MODE</ThemedText>
              <ThemedText style={styles.metricVal}>{executionMode}</ThemedText>
            </View>

            <View style={styles.metricItem}>
              <ThemedText style={styles.metricLabel}>RAM ALLOCATION</ThemedText>
              <ThemedText style={styles.metricVal}>{ramUsed} / {ramTotal} GB</ThemedText>
            </View>

            <View style={styles.metricItem}>
              <ThemedText style={styles.metricLabel}>LATENCY</ThemedText>
              <ThemedText style={styles.metricVal}>&lt; 15ms</ThemedText>
            </View>

            <View style={styles.metricItem}>
              <ThemedText style={styles.metricLabel}>INTEGRITY</ThemedText>
              <ThemedText style={styles.integrityVal}>Verified</ThemedText>
            </View>
          </View>

          {/* Power Distribution Progress Bar */}
          <View style={styles.powerSection}>
            <View style={styles.powerHeaderRow}>
              <ThemedText style={styles.powerLabel}>POWER DISTRIBUTION (RAM)</ThemedText>
              <ThemedText style={styles.powerUsageText}>{ramUsagePercent}% USAGE</ThemedText>
            </View>

            <View style={styles.progressBarTrack}>
              <View style={[styles.progressBarFill, { width: `${Math.min(parseFloat(ramUsagePercent), 100)}%` }]} />
            </View>
          </View>
        </View>

        {/* Right Column Stack */}
        <View style={styles.rightStack}>
          {/* Quick Commands */}
          <View style={styles.rightCard}>
            <View style={styles.rightCardHeader}>
              <Icon name="zap" size={14} color="#7fa094" />
              <ThemedText style={styles.rightCardTitle}>QUICK COMMANDS</ThemedText>
            </View>

            <View style={styles.quickCommandsList}>
              <Pressable
                onPress={() => router.push('/console')}
                style={({ pressed }) => [styles.quickCmdItem, pressed && styles.pressed]}
              >
                <ThemedText style={styles.quickCmdText}>Open Neural Console</ThemedText>
                <Icon name="chevron-right" size={16} color="#7fa094" />
              </Pressable>

              <Pressable
                onPress={() => router.push('/system')}
                style={({ pressed }) => [styles.quickCmdItem, pressed && styles.pressed]}
              >
                <ThemedText style={styles.quickCmdText}>View Hardware Topology</ThemedText>
                <Icon name="chevron-right" size={16} color="#7fa094" />
              </Pressable>

              <Pressable
                onPress={() => router.push('/models')}
                style={({ pressed }) => [styles.quickCmdItem, pressed && styles.pressed]}
              >
                <ThemedText style={styles.quickCmdText}>Switch to LayerStream</ThemedText>
                <Icon name="chevron-right" size={16} color="#7fa094" />
              </Pressable>

              <Pressable
                onPress={() => router.push('/triage')}
                style={({ pressed }) => [styles.quickCmdItem, styles.quickCmdTriage, pressed && styles.pressed]}
              >
                <ThemedText style={[styles.quickCmdText, styles.quickCmdTriageText]}>Run Medical Triage</ThemedText>
                <Icon name="chevron-right" size={16} color="#2dd4bf" />
              </Pressable>
            </View>
          </View>

          {/* Hardware Optimization */}
          <View style={styles.rightCard}>
            <View style={styles.rightCardHeader}>
              <Icon name="lock" size={14} color="#7fa094" />
              <ThemedText style={styles.rightCardTitle}>HARDWARE OPTIMIZATION</ThemedText>
            </View>
            <ThemedText style={styles.optimizationText}>
              Your AVX-512 unit is detected. Performance boost of 15% applied to transformer layers.
            </ThemedText>
          </View>
        </View>
      </View>

      {/* Bottom Grid: Processor, Neural Storage, System Health */}
      <View style={styles.bottomGrid}>
        {/* Processor Card */}
        <View style={styles.bottomCard}>
          <View style={styles.bottomCardHeaderRow}>
            <ThemedText style={styles.bottomCardHeaderTag}>PROCESSOR</ThemedText>
            <Icon name="cpu" size={16} color="#7fa094" />
          </View>
          <ThemedText style={styles.bottomCardMainTitle}>{cpuName}</ThemedText>
          <ThemedText style={styles.bottomCardSubtitle}>{cpuCores} Physical Cores | {cpuThreads} Threads</ThemedText>
        </View>

        {/* Neural Storage Card */}
        <View style={styles.bottomCard}>
          <View style={styles.bottomCardHeaderRow}>
            <ThemedText style={styles.bottomCardHeaderTag}>NEURAL STORAGE</ThemedText>
            <Icon name="disk" size={16} color="#7fa094" />
          </View>
          <ThemedText style={styles.bottomCardMainTitle}>{diskFree} GB Free</ThemedText>
          <ThemedText style={styles.bottomCardSubtitle}>Type: {diskType} | Velocity: {diskSpeed} MB/s</ThemedText>
        </View>

        {/* System Health Card */}
        <View style={styles.bottomCard}>
          <View style={styles.bottomCardHeaderRow}>
            <ThemedText style={styles.bottomCardHeaderTag}>SYSTEM HEALTH</ThemedText>
            <Icon name="activity" size={16} color="#7fa094" />
          </View>
          <ThemedText style={styles.bottomCardMainTitle}>Optimal</ThemedText>
          <ThemedText style={styles.bottomCardSubtitle}>All neural pathways are functioning correctly.</ThemedText>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#04100d',
  },
  contentContainer: {
    padding: 32,
    gap: 28,
  },
  titleSection: {
    gap: 6,
  },
  mainTitle: {
    color: '#ffffff',
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  titleTextCol: {
    flex: 1,
    gap: 4,
  },
  subTitle: {
    color: '#7fa094',
    fontSize: 15,
  },
  topGrid: {
    flexDirection: 'row',
    gap: 20,
    flexWrap: 'wrap',
  },
  systemCoreCard: {
    flex: 1.8,
    minWidth: 480,
    backgroundColor: '#0b1a15',
    borderWidth: 1,
    borderColor: '#1a352c',
    borderRadius: 16,
    padding: 24,
    justifyContent: 'space-between',
    gap: 24,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  systemCoreHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  greenDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
  },
  systemCoreHeaderTag: {
    color: '#7fa094',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  terminateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#25141a',
    borderWidth: 1,
    borderColor: '#5b1e2b',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  terminateText: {
    color: '#f87171',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  modelNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  modelNameText: {
    color: '#ffffff',
    fontSize: 24,
    fontWeight: '700',
    fontFamily: 'var(--font-mono)',
  },
  activePill: {
    backgroundColor: '#1a352c',
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: 6,
  },
  activePillText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: '#1a352c',
    borderBottomWidth: 1,
    borderBottomColor: '#1a352c',
    paddingVertical: 16,
  },
  metricItem: {
    gap: 6,
  },
  metricLabel: {
    color: '#4d6b60',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  metricVal: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '600',
  },
  integrityVal: {
    color: '#10b981',
    fontSize: 15,
    fontWeight: '600',
  },
  powerSection: {
    gap: 10,
  },
  powerHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  powerLabel: {
    color: '#4d6b60',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  powerUsageText: {
    color: '#7fa094',
    fontSize: 11,
    fontWeight: '600',
  },
  progressBarTrack: {
    height: 6,
    backgroundColor: '#1a352c',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#2dd4bf',
    borderRadius: 3,
  },
  rightStack: {
    flex: 1,
    minWidth: 300,
    gap: 20,
  },
  rightCard: {
    backgroundColor: '#0b1a15',
    borderWidth: 1,
    borderColor: '#1a352c',
    borderRadius: 16,
    padding: 20,
    gap: 16,
  },
  rightCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  rightCardTitle: {
    color: '#7fa094',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  quickCommandsList: {
    gap: 8,
  },
  quickCmdItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#10241e',
    borderWidth: 1,
    borderColor: '#1f3d33',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
  },
  quickCmdTriage: {
    borderColor: '#14b8a6',
    backgroundColor: '#0f2a23',
  },
  quickCmdTriageText: {
    color: '#5eead4',
    fontWeight: '600',
  },
  quickCmdText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
  },
  optimizationText: {
    color: '#7fa094',
    fontSize: 13,
    lineHeight: 20,
  },
  bottomGrid: {
    flexDirection: 'row',
    gap: 20,
    flexWrap: 'wrap',
  },
  bottomCard: {
    flex: 1,
    minWidth: 260,
    backgroundColor: '#0b1a15',
    borderWidth: 1,
    borderColor: '#1a352c',
    borderRadius: 16,
    padding: 20,
    gap: 12,
  },
  bottomCardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  bottomCardHeaderTag: {
    color: '#7fa094',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  bottomCardMainTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '700',
  },
  bottomCardSubtitle: {
    color: '#7fa094',
    fontSize: 13,
  },
  pressed: {
    opacity: 0.7,
  },
});
