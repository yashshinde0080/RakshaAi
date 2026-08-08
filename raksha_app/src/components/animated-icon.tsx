import * as SplashScreen from 'expo-splash-screen';
import { useState } from 'react';
import { Dimensions, StyleSheet, Text, View } from 'react-native';
import Animated, { Easing, Keyframe } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

const INITIAL_SCALE_FACTOR = Dimensions.get('screen').height / 90;
const DURATION = 600;

// Raksha AI monogram tile: teal shield-tile + "R" + a heartbeat pulse.
function MarkTile() {
  return (
    <View style={styles.tile}>
      <Text style={styles.monogram}>R</Text>
      <View style={styles.pulse}>
        <View style={[styles.tick, styles.tickShort]} />
        <View style={[styles.tick, styles.tickTall]} />
        <View style={[styles.tick, styles.tickMid]} />
      </View>
    </View>
  );
}

export function AnimatedSplashOverlay() {
  const [animate, setAnimate] = useState(false);
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  const splashKeyframe = new Keyframe({
    0: {
      transform: [{ scale: 1 }],
      opacity: 1,
    },
    20: {
      opacity: 1,
    },
    70: {
      opacity: 0,
      easing: Easing.elastic(0.7),
    },
    100: {
      opacity: 0,
      transform: [{ scale: 1 }],
      easing: Easing.elastic(0.7),
    },
  });

  return animate ? (
    <Animated.View
      entering={splashKeyframe.duration(DURATION).withCallback((finished) => {
        'worklet';
        if (finished) {
          scheduleOnRN(setVisible, false);
        }
      })}
      style={styles.splashOverlay}>
      <MarkTile />
    </Animated.View>
  ) : (
    <View
      onLayout={() => {
        SplashScreen.hideAsync().finally(() => {
          setAnimate(true);
        });
      }}
      style={styles.splashOverlay}>
      <MarkTile />
    </View>
  );
}

const keyframe = new Keyframe({
  0: {
    transform: [{ scale: INITIAL_SCALE_FACTOR }],
  },
  100: {
    transform: [{ scale: 1 }],
    easing: Easing.elastic(0.7),
  },
});

const logoKeyframe = new Keyframe({
  0: {
    transform: [{ scale: 1.3 }],
    opacity: 0,
  },
  40: {
    transform: [{ scale: 1.3 }],
    opacity: 0,
    easing: Easing.elastic(0.7),
  },
  100: {
    opacity: 1,
    transform: [{ scale: 1 }],
    easing: Easing.elastic(0.7),
  },
});

export function AnimatedIcon() {
  return (
    <View style={styles.iconContainer}>
      <Animated.View entering={keyframe.duration(DURATION)} style={styles.background}>
        <Animated.View entering={logoKeyframe.duration(DURATION)} style={styles.inner}>
          <MarkTile />
        </Animated.View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  iconContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    width: 128,
    height: 128,
    zIndex: 100,
  },
  background: {
    borderRadius: 40,
    experimental_backgroundImage: `linear-gradient(180deg, #14b8a6, #0f766e)`,
    width: 128,
    height: 128,
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  inner: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  tile: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  monogram: {
    color: '#ffffff',
    fontSize: 52,
    fontWeight: '800',
    letterSpacing: -2,
    lineHeight: 56,
  },
  pulse: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 4,
    height: 20,
  },
  tick: {
    width: 4,
    borderRadius: 2,
    backgroundColor: '#04100d',
  },
  tickShort: {
    height: 8,
  },
  tickMid: {
    height: 13,
  },
  tickTall: {
    height: 20,
  },
  splashOverlay: {
    ...StyleSheet.absoluteFill,
    experimental_backgroundImage: `linear-gradient(180deg, #14b8a6, #0f766e)`,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
});
