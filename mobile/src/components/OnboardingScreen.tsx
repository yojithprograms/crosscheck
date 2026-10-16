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

/**
 * The frame shared by the first-run screens: two soft blue circles in the corners, server banner on top,
 * scrolling content, and a footer pinned to the bottom on its own white panel.
 */
export function OnboardingScreen({ children, footer }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.screen, { paddingTop: insets.top }]}>
      <View style={styles.circleTop} pointerEvents="none" importantForAccessibility="no-hide-descendants" />
      <View style={styles.circleSide} pointerEvents="none" importantForAccessibility="no-hide-descendants" />
      <ServerBanner />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
      <View style={[styles.footer, { paddingBottom: Math.max(insets.bottom, spacing.lg) }]}>{footer}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, overflow: "hidden" },
  // Decorative only: big pastel circles peeking in from the edges.
  circleTop: {
    position: "absolute",
    top: -120,
    right: -90,
    width: 280,
    height: 280,
    borderRadius: 140,
    backgroundColor: colors.brandSoft,
    opacity: 0.7,
  },
  circleSide: {
    position: "absolute",
    top: 160,
    left: -110,
    width: 190,
    height: 190,
    borderRadius: 95,
    backgroundColor: colors.brandTint,
  },
  content: { padding: shape.screenPadding, gap: spacing.lg, flexGrow: 1 },
  footer: {
    paddingHorizontal: shape.screenPadding,
    paddingTop: spacing.md,
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderTopLeftRadius: shape.sheetRadius,
    borderTopRightRadius: shape.sheetRadius,
    shadowColor: colors.shadow,
    shadowOpacity: 0.1,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: -6 },
    elevation: 10,
  },
});
