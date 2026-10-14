import { StyleSheet, Text, View } from "react-native";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

/** "Why" and a bulleted list of plain-English reasons. Used by the street card and the hazard card. */
export function ReasonList({ reasons }: { reasons: string[] }) {
  const items = reasons.length > 0 ? reasons : [strings.cards.noReasons];
  return (
    <View style={styles.wrap}>
      <Text style={styles.heading}>{strings.cards.why}</Text>
      {items.map((reason) => (
        <View key={reason} style={styles.row}>
          <Text style={styles.text}>•</Text>
          <Text style={[styles.text, styles.reason]}>{reason}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm, marginTop: spacing.sm },
  heading: { ...type.headline, color: colors.text },
  row: { flexDirection: "row", gap: spacing.sm },
  text: { ...type.body, color: colors.text },
  reason: { flex: 1 },
});
