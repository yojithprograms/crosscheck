import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import type { ComponentProps } from "react";
import type { ColorValue } from "react-native";

import { AppHeader } from "@/components/AppHeader";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";

type IconName = ComponentProps<typeof Ionicons>["name"];

function tabIcon(filled: IconName, outline: IconName) {
  return ({ color, focused }: { color: ColorValue; focused: boolean }) => (
    <Ionicons name={focused ? filled : outline} size={26} color={color} />
  );
}

/** The four tabs (APP_FLOW §1): Map, Route, Report, School. The active tab is teal. */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
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
