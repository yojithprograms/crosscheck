import type { ReactNode } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ServerBanner } from "@/components/ServerBanner";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";

type Props = {
  children: ReactNode; // the scrolling content
  footer: ReactNode; // page dots and the main button, pinned to the bottom
};

/** The frame shared by the first-run screens: server banner on top, scrolling content, pinned footer. */
export function OnboardingScreen({ children, footer }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: Math.max(insets.bottom, spacing.lg) }]}>
      <ServerBanner />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
      <View style={styles.footer}>{footer}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: shape.screenPadding, gap: spacing.lg, flexGrow: 1 },
  footer: { paddingHorizontal: shape.screenPadding, gap: spacing.sm },
});
