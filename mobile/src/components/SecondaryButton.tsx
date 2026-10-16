import { StyleSheet, Text } from "react-native";

import { PressableScale } from "@/components/PressableScale";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = { title: string; onPress: () => void; disabled?: boolean };

/** The second-choice button: a pale blue fill with dark blue text, same size as the primary one. */
export function SecondaryButton({ title, onPress, disabled }: Props) {
  return (
    <PressableScale
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      style={[styles.button, disabled && styles.disabled]}
      pressedStyle={styles.pressed}
    >
      <Text style={[styles.text, disabled && styles.disabledText]}>{title}</Text>
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  button: {
    height: shape.buttonHeight,
    borderRadius: shape.cardRadius,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  pressed: { backgroundColor: colors.brandSky },
  disabled: { backgroundColor: colors.hairline },
  text: { ...type.headline, color: colors.brandDark },
  disabledText: { color: colors.disabledText },
});
