import { StyleSheet, Text, View } from "react-native";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

/** "Why" and a short list of plain-English reasons, in a pale blue panel. Used by the street card and the hazard card. */
export function ReasonList({ reasons }: { reasons: string[] }) {
  const items = reasons.length > 0 ? reasons : [strings.cards.noReasons];
  return (
    <View style={styles.wrap}>
      <Text style={styles.heading}>{strings.cards.why}</Text>
      {items.map((reason) => (
        <View key={reason} style={styles.row}>
          <View style={styles.bullet} />
          <Text style={[styles.text, styles.reason]}>{reason}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
    marginTop: spacing.sm,
    padding: spacing.lg,
    borderRadius: shape.cardRadius,
    backgroundColor: colors.bg,
  },
  heading: { ...type.headline, color: colors.text },
  row: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  bullet: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.brand, marginTop: 9 },
  text: { ...type.body, color: colors.text },
  reason: { flex: 1 },
});
