import { Ionicons } from "@expo/vector-icons";
import { StyleSheet, Text, View } from "react-native";

import type { Hazard } from "@/api/types";
import { NumberBadge } from "@/components/NumberBadge";
import { PressableScale } from "@/components/PressableScale";
import { RiskBadge } from "@/components/RiskBadge";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = { hazard: Hazard; onPress: () => void; last?: boolean };

/** One line in the list of spots on a route: number, title, and risk badge. Tap it to open the hazard card. */
export function HazardRow({ hazard, onPress, last }: Props) {
  return (
    <PressableScale
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={strings.hazards.rowLabel(hazard.n, hazard.title, strings.risk[hazard.risk_class])}
      style={[styles.row, !last && styles.divider]}
      scaleTo={0.99}
    >
      <NumberBadge n={hazard.n} kind={hazard.kind} />
      <View style={styles.texts}>
        <Text style={styles.title}>{hazard.title}</Text>
        <RiskBadge riskClass={hazard.risk_class} />
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: shape.minTouchTarget + spacing.lg,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  divider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  texts: { flex: 1, gap: spacing.xs },
  title: { ...type.body, color: colors.text },
});
