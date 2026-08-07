import { StyleSheet, Text, View } from 'react-native';

import { t } from '../i18n';
import { TriageResult } from '../types';

interface Props {
  result: TriageResult;
  /** Compact inline variant (result screen header row) vs. large hero badge. */
  variant?: 'hero' | 'inline';
}

/** Color-coded severity display (TRD §3). */
export function SeverityBadge({ result, variant = 'hero' }: Props) {
  const hero = variant === 'hero';
  const { color, label } = result;

  return (
    <View
      style={[
        styles.badge,
        hero ? styles.hero : styles.inline,
        { backgroundColor: color },
      ]}>
      <Text style={[styles.level, hero ? styles.levelHero : styles.levelInline]}>
        {t('severity.levelName', { level: result.level })}
      </Text>
      <Text style={[styles.label, hero ? styles.labelHero : styles.labelInline]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  hero: {
    borderRadius: 24,
    paddingVertical: 28,
    paddingHorizontal: 24,
    gap: 4,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  inline: {
    borderRadius: 12,
    paddingVertical: 6,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    alignSelf: 'flex-start',
  },
  level: {
    fontWeight: '800',
    letterSpacing: 1,
    color: '#FFFFFF',
  },
  levelHero: {
    fontSize: 20,
  },
  levelInline: {
    fontSize: 12,
  },
  label: {
    color: '#FFFFFF',
    textAlign: 'center',
  },
  labelHero: {
    fontSize: 26,
    fontWeight: '700',
  },
  labelInline: {
    fontSize: 13,
    fontWeight: '700',
  },
});
