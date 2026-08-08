import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { Colors } from '@/constants/theme';

export default function AppTabs() {
  const colors = Colors.dark;

  return (
    <NativeTabs
      backgroundColor={colors.background}
      indicatorColor={colors.backgroundSelected}
      labelStyle={{ selected: { color: colors.text } }}>
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="house.fill" md="home" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="console">
        <NativeTabs.Trigger.Label>Console</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="terminal.fill" md="terminal" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="models">
        <NativeTabs.Trigger.Label>Models</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="memorychip.fill" md="memory" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="documents">
        <NativeTabs.Trigger.Label>Docs</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="doc.fill" md="description" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="benchmark">
        <NativeTabs.Trigger.Label>Benchmark</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="bolt.fill" md="flash_on" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="system">
        <NativeTabs.Trigger.Label>System</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="gauge" md="speed" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="settings">
        <NativeTabs.Trigger.Label>Settings</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="gearshape.fill" md="settings" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
