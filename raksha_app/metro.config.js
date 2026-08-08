// Learn more: https://docs.expo.dev/guides/customizing-metro/
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// expo-sqlite's web backend (wa-sqlite) imports a .wasm asset — Metro only
// resolves it once wasm is a registered asset extension.
config.resolver.assetExts.push('wasm');

module.exports = config;
