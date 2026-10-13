import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { RiskClass } from "@/api/types";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

const looks: Record<RiskClass, { icon: ComponentProps<typeof Ionicons>["name"]; color: string; label: string }> = {
  high: { icon: "warning", color: colors.riskHigh, label: strings.risk.high },
  medium: { icon: "alert-circle", color: "#B45309", label: strings.risk.medium },
  low: { icon: "checkmark-circle", color: colors.textMuted, label: strings.risk.low },
};

/** "High risk" / "Medium risk" / "Lower risk": always a word and an icon, never just a color. */
export function RiskBadge({ riskClass }: { riskClass: RiskClass }) {
  const { icon, color, label } = looks[riskClass];
  return (
    <View style={[styles.badge, { borderColor: color }]} accessible accessibilityLabel={label}>
      <Ionicons name={icon} size={16} color={color} />
      <Text style={[styles.label, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    borderWidth: 1.5,
    borderRadius: 999,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    alignSelf: "flex-start",
  },
  label: { ...type.caption, fontWeight: "600" },
});
