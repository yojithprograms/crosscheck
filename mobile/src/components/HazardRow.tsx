import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { Hazard } from "@/api/types";
import { NumberBadge } from "@/components/NumberBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

/** One line in the list of spots on a route: number, title, and risk badge. Tap it to open the hazard card. */
export function HazardRow({ hazard, onPress }: { hazard: Hazard; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={strings.hazards.rowLabel(hazard.n, hazard.title, strings.risk[hazard.risk_class])}
      style={styles.row}
    >
      <NumberBadge n={hazard.n} kind={hazard.kind} />
      <View style={styles.texts}>
        <Text style={styles.title}>{hazard.title}</Text>
        <RiskBadge riskClass={hazard.risk_class} />
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: shape.minTouchTarget + spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  texts: { flex: 1, gap: spacing.xs },
  title: { ...type.body, color: colors.text },
});
