import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { ActivityIndicator, StyleSheet, Text } from "react-native";

import { PressableScale } from "@/components/PressableScale";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  icon?: ComponentProps<typeof Ionicons>["name"];
};

/** The main button on a screen: full width, 56 tall, solid blue with a soft glow. */
export function PrimaryButton({ title, onPress, disabled, loading, icon }: Props) {
  const inactive = disabled || loading;
  return (
    <PressableScale
      onPress={onPress}
      disabled={inactive}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      style={[styles.button, disabled && !loading && styles.disabled]}
      pressedStyle={styles.pressed}
    >
      {loading ? (
        <ActivityIndicator color={colors.onBrand} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={22} color={disabled ? colors.disabledText : colors.onBrand} /> : null}
          <Text style={[styles.text, disabled && styles.disabledText]}>{title}</Text>
        </>
      )}
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  button: {
    height: shape.buttonHeight,
    borderRadius: shape.cardRadius,
    backgroundColor: colors.brand,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    shadowColor: colors.brand,
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 4,
  },
  pressed: { backgroundColor: colors.brandDark },
  disabled: { backgroundColor: colors.disabledBg, shadowOpacity: 0, elevation: 0 },
  text: { ...type.headline, color: colors.onBrand },
  disabledText: { color: colors.disabledText },
});
