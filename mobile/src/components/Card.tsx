import type { ReactNode } from "react";
import { Pressable, StyleSheet, View } from "react-native";

import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";

type Props = { children: ReactNode; onPress?: () => void };

/** A rounded surface for grouped content. Pass onPress to make the whole card tappable. */
export function Card({ children, onPress }: Props) {
  if (onPress) {
    return (
      <Pressable onPress={onPress} accessibilityRole="button" style={styles.card}>
        {children}
      </Pressable>
    );
  }
  return <View style={styles.card}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.xs,
  },
});
