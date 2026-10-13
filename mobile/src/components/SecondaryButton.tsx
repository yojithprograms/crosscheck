import { Pressable, StyleSheet, Text } from "react-native";

import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = { title: string; onPress: () => void; disabled?: boolean };

/** The second-choice button: white with a teal outline, same size as the primary one. */
export function SecondaryButton({ title, onPress, disabled }: Props) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [styles.button, disabled && styles.disabled, pressed && !disabled && styles.pressed]}
    >
      <Text style={[styles.text, disabled && styles.disabledText]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    height: shape.buttonHeight,
    borderRadius: shape.cardRadius,
    borderWidth: 2,
    borderColor: colors.brand,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  pressed: { backgroundColor: colors.surface },
  disabled: { borderColor: colors.riskLow },
  text: { ...type.headline, color: colors.brand },
  disabledText: { color: colors.riskLow },
});
