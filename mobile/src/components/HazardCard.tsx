import { StyleSheet, Text, View } from "react-native";

import type { Hazard } from "@/api/types";
import { ReasonList } from "@/components/ReasonList";
import { RiskBadge } from "@/components/RiskBadge";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { percentileText } from "@/utils/format";

type Props = { hazard: Hazard; onReport: () => void };

/** S9 · the card for one spot on a route: how risky it is, why, what to do there, and a way to report it. */
export function HazardCard({ hazard, onReport }: Props) {
  // Crossings and intersections get the "cross carefully" tip. Everything else is about walking along a road.
  const crossing = hazard.kind === "crossing" || hazard.kind === "intersection";
  return (
    <View style={styles.wrap}>
      <Text style={styles.title} accessibilityRole="header">
        {strings.hazards.cardTitle(hazard.n, hazard.title)}
      </Text>
      <RiskBadge riskClass={hazard.risk_class} />
      <Text style={styles.body}>{percentileText(hazard.risk_pct)}</Text>

      <ReasonList reasons={hazard.reasons} />

      <Text style={styles.section}>{strings.hazards.tipsTitle}</Text>
      <Text style={styles.body}>{crossing ? strings.hazards.tipCrossing : strings.hazards.tipAlong}</Text>

      <View style={styles.button}>
        <SecondaryButton title={strings.hazards.report} onPress={onReport} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  title: { ...type.sectionTitle, color: colors.text, paddingRight: shape.minTouchTarget },
  section: { ...type.headline, color: colors.text, marginTop: spacing.sm },
  body: { ...type.body, color: colors.text },
  button: { marginTop: spacing.md },
});
