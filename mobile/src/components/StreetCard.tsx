import { useRouter } from "expo-router";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { useSegment } from "@/api/hooks";
import { RiskBadge } from "@/components/RiskBadge";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { approx, percentileText, sidewalkText } from "@/utils/format";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text style={styles.factValue}>{value}</Text>
    </View>
  );
}

/** S5 · the card for a tapped street: risk, plain-English reasons, and a few facts. */
export function StreetCard({ schoolId, segId }: { schoolId: string; segId: string }) {
  const router = useRouter();
  const segment = useSegment(schoolId, segId);

  if (segment.isPending) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand} accessibilityLabel={strings.cards.loading} />
      </View>
    );
  }
  if (segment.isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.body}>{strings.cards.loadError}</Text>
        <Pressable onPress={() => void segment.refetch()} accessibilityRole="button" style={styles.retry}>
          <Text style={styles.link}>{strings.cards.retry}</Text>
        </Pressable>
      </View>
    );
  }

  const s = segment.data;
  const reasons = s.reasons.length > 0 ? s.reasons : [strings.cards.noReasons];
  return (
    <View style={styles.wrap}>
      <Text style={styles.title} accessibilityRole="header">
        {s.name}
      </Text>
      <RiskBadge riskClass={s.risk_class} />
      <Text style={styles.body}>{percentileText(s.risk_pct)}</Text>

      <Text style={styles.section}>{strings.cards.why}</Text>
      {reasons.map((reason) => (
        <View key={reason} style={styles.reasonRow}>
          <Text style={styles.bullet}>•</Text>
          <Text style={[styles.body, styles.reasonText]}>{reason}</Text>
        </View>
      ))}
      {s.crashes_prelim > 0 ? <Text style={styles.caption}>{strings.cards.preliminary(s.crashes_prelim)}</Text> : null}

      <View style={styles.facts}>
        <Fact
          label={strings.cards.speedLimit}
          value={strings.cards.mph(approx(s.speed_mph, s.speed_imputed))}
        />
        <Fact label={strings.cards.lanes} value={approx(s.lanes, false)} />
        <Fact label={strings.cards.sidewalk} value={sidewalkText(s.sidewalk_cov, s.sidewalk_known)} />
      </View>

      {s.reports_recent > 0 ? <Text style={styles.body}>{strings.cards.reportsHere(s.reports_recent)}</Text> : null}

      <Pressable onPress={() => router.push("/how-it-works")} accessibilityRole="link" style={styles.linkWrap}>
        <Text style={styles.link}>{strings.cards.howCalculated}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  center: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xl },
  title: { ...type.sectionTitle, color: colors.text, paddingRight: shape.minTouchTarget },
  section: { ...type.headline, color: colors.text, marginTop: spacing.sm },
  body: { ...type.body, color: colors.text },
  caption: { ...type.caption, color: colors.textMuted },
  reasonRow: { flexDirection: "row", gap: spacing.sm },
  bullet: { ...type.body, color: colors.text },
  reasonText: { flex: 1 },
  facts: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  fact: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: 2,
  },
  factLabel: { ...type.caption, color: colors.textMuted },
  factValue: { ...type.headline, color: colors.text },
  linkWrap: { minHeight: shape.minTouchTarget, justifyContent: "center" },
  retry: { minHeight: shape.minTouchTarget, justifyContent: "center" },
  link: { ...type.body, color: colors.brand, textDecorationLine: "underline" },
});
