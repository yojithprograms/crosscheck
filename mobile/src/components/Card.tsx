import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";

import { PressableScale } from "@/components/PressableScale";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { shadow } from "@/theme/shadow";

type Props = { children: ReactNode; onPress?: () => void };

/** A white rounded card with a soft shadow, for grouped content. Pass onPress to make the whole card tappable. */
export function Card({ children, onPress }: Props) {
  if (onPress) {
    return (
      <PressableScale onPress={onPress} accessibilityRole="button" style={styles.card} scaleTo={0.98}>
        {children}
      </PressableScale>
    );
  }
  return <View style={styles.card}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    borderWidth: 1,
    borderColor: colors.hairline,
    padding: spacing.lg,
    gap: spacing.xs,
    ...shadow.card,
  },
});
