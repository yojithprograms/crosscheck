import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

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

/** The main button on a screen: full width, 52 tall, teal. */
export function PrimaryButton({ title, onPress, disabled, loading, icon }: Props) {
  const inactive = disabled || loading;
  return (
    <Pressable
      onPress={onPress}
      disabled={inactive}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      style={({ pressed }) => [styles.button, inactive && styles.disabled, pressed && !inactive && styles.pressed]}
    >
      {loading ? (
        <ActivityIndicator color={colors.onBrand} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={22} color={colors.onBrand} /> : null}
          <Text style={styles.text}>{title}</Text>
        </>
      )}
    </Pressable>
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
  },
  pressed: { backgroundColor: colors.brandDark },
  disabled: { backgroundColor: colors.riskLow },
  text: { ...type.headline, color: colors.onBrand },
});
