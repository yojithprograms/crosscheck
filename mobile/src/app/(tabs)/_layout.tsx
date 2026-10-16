import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import type { ComponentProps } from "react";
import { StyleSheet, View, type ColorValue } from "react-native";

import { AppHeader } from "@/components/AppHeader";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";

type IconName = ComponentProps<typeof Ionicons>["name"];

// The active tab gets a filled icon on a pale blue pill, so it is clear without relying on color alone.
function tabIcon(filled: IconName, outline: IconName) {
  return ({ color, focused }: { color: ColorValue; focused: boolean }) => (
    <View style={[styles.pill, focused && styles.pillActive]}>
      <Ionicons name={focused ? filled : outline} size={24} color={color} />
    </View>
  );
}

/** The four tabs (APP_FLOW §1): Map, Route, Report, School. The active tab is blue. */
export default function TabsLayout() {
  const onboarded = useAppStore((state) => state.onboarded);
  if (!onboarded) return <Redirect href="/onboarding/welcome" />; // first launch (or after Reset app)
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
        tabBarStyle: { backgroundColor: colors.surface, borderTopWidth: 0, ...shadow.raised },
        sceneStyle: { backgroundColor: colors.bg },
        header: ({ options }) => <AppHeader title={options.title ?? strings.appName} />,
      }}
    >
      <Tabs.Screen name="index" options={{ title: strings.tabs.map, tabBarIcon: tabIcon("map", "map-outline") }} />
      <Tabs.Screen name="route" options={{ title: strings.tabs.route, tabBarIcon: tabIcon("navigate", "navigate-outline") }} />
      <Tabs.Screen name="report" options={{ title: strings.tabs.report, tabBarIcon: tabIcon("megaphone", "megaphone-outline") }} />
      <Tabs.Screen name="school" options={{ title: strings.tabs.school, tabBarIcon: tabIcon("school", "school-outline") }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  pill: { width: 56, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  pillActive: { backgroundColor: colors.brandSoft },
});
