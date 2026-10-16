import { QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";

import { useServerWake } from "@/api/hooks";
import { connectReactQueryToPhone, queryClient } from "@/api/queryClient";
import { AskAdult } from "@/components/AskAdult";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { type } from "@/theme/type";

/** S0: the launch screen, shown while the saved settings load from the device. */
function LaunchScreen() {
  return (
    <View style={styles.launch}>
      <View style={styles.circleOne} />
      <View style={styles.circleTwo} />
      <Text style={styles.logo}>{strings.appName}</Text>
      <Text style={styles.loading}>{strings.launch.loading}</Text>
    </View>
  );
}

/**
 * Starts waking the server as soon as the app opens, then shows the screens. If the saved age answer is
 * "Under 13", the app stops at the ask-an-adult message every time it opens.
 */
function AppStack() {
  useServerWake();
  const ageGate = useAppStore((state) => state.ageGate);
  if (ageGate === "under13") return <AskAdult />;
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        // The two modal screens (Settings, How risk scores work) share the app's soft blue look.
        headerTintColor: colors.brandDark,
        headerTitleStyle: { color: colors.text, fontWeight: "700" },
        headerStyle: { backgroundColor: colors.surface },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Screen name="onboarding" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen
        name="settings"
        options={{ presentation: "modal", headerShown: true, title: strings.header.settings }}
      />
      <Stack.Screen
        name="how-it-works"
        options={{ presentation: "modal", headerShown: true, title: strings.howItWorks.title }}
      />
    </Stack>
  );
}

export default function RootLayout() {
  const hydrated = useAppStore((state) => state.hydrated);

  useEffect(() => connectReactQueryToPhone(), []);

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style={hydrated ? "dark" : "light"} />
      {hydrated ? <AppStack /> : <LaunchScreen />}
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  launch: {
    flex: 1,
    backgroundColor: colors.brand,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    overflow: "hidden",
  },
  // Decorative pastel circles behind the name.
  circleOne: { position: "absolute", top: -90, left: -70, width: 260, height: 260, borderRadius: 130, backgroundColor: colors.onBrand, opacity: 0.1 },
  circleTwo: { position: "absolute", bottom: -110, right: -80, width: 300, height: 300, borderRadius: 150, backgroundColor: colors.onBrand, opacity: 0.08 },
  logo: { ...type.screenTitle, fontSize: 36, lineHeight: 42, color: colors.onBrand },
  loading: { ...type.body, color: colors.brandSoft },
});
