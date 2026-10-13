import { StyleSheet, Text, View } from "react-native";

import type { CrashFeature } from "@/api/types";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { crashSeverityText, monthYear } from "@/utils/format";

/** S5 · the card for a tapped crash dot. It never shows report numbers or exact dates. */
export function CrashCard({ crash }: { crash: CrashFeature }) {
  const { mode, year, month, severity, prelim } = crash.properties;
  return (
    <View style={styles.wrap}>
      <Text style={styles.title} accessibilityRole="header">
        {strings.cards.crashTitle(mode)}
      </Text>
      <Text style={styles.body}>
        {monthYear(year, month)} · {crashSeverityText(severity)}
      </Text>
      <Text style={styles.caption}>{strings.cards.crashSource}</Text>
      {prelim ? <Text style={styles.caption}>{strings.cards.crashPreliminary}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  title: { ...type.sectionTitle, color: colors.text, paddingRight: shape.minTouchTarget },
  body: { ...type.body, color: colors.text },
  caption: { ...type.caption, color: colors.textMuted },
});
