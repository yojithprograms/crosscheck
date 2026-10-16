import { Ionicons } from "@expo/vector-icons";
import { StyleSheet, Text, View } from "react-native";

import type { Route, RouteKind } from "@/api/types";
import { PressableScale } from "@/components/PressableScale";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { miles, minutes } from "@/utils/format";

type Props = {
  route: Route;
  kind: RouteKind | "same"; // "same": the fastest route is also the lower-risk one, so there is one card
  selected: boolean;
  onPress?: () => void; // leave out for "same": there is nothing to switch to
};

const LABELS = { fastest: strings.results.fastest, lower_risk: strings.results.lowerRisk, same: strings.results.both };

/** A tiny sample of the route's line on the map: solid blue for lower-risk, dashed gray for fastest. */
function LineSample({ kind }: { kind: Props["kind"] }) {
  const dashed = kind === "fastest";
  return (
    <View
      style={[styles.sample, dashed ? styles.sampleDashed : styles.sampleSolid]}
      importantForAccessibility="no-hide-descendants"
      accessibilityElementsHidden
    />
  );
}

/**
 * S8 · one route's summary: time, distance, and how many high-risk spots it passes. The selected card gets a
 * blue border, a pale blue fill, and a filled radio dot, so it never depends on color alone.
 */
export function RouteCard({ route, kind, selected, onPress }: Props) {
  const label = LABELS[kind];
  const time = minutes(route.duration_min);
  const distance = miles(route.distance_m);
  const spots = strings.results.spots(route.high_count);
  const hasHighRisk = route.high_count > 0;

  return (
    <PressableScale
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? "button" : "summary"}
      accessibilityState={{ selected }}
      accessibilityLabel={strings.results.cardLabel(label, time, distance, spots, selected)}
      style={[styles.card, selected && styles.selected]}
      scaleTo={0.98}
    >
      <View style={styles.header}>
        {onPress ? (
          <Ionicons
            name={selected ? "radio-button-on" : "radio-button-off"}
            size={20}
            color={selected ? colors.brand : colors.textMuted}
          />
        ) : null}
        <Text style={styles.label}>{label}</Text>
      </View>
      <LineSample kind={kind} />
      <Text style={styles.time}>{time}</Text>
      <Text style={styles.distance}>{distance}</Text>
      <View style={[styles.spots, hasHighRisk && styles.spotsWarn]}>
        <Ionicons
          name={hasHighRisk ? "warning" : "checkmark-circle"}
          size={16}
          color={hasHighRisk ? colors.riskHigh : colors.textMuted}
        />
        <Text style={styles.spotsText}>{spots}</Text>
      </View>
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  card: {
    flexGrow: 1,
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    borderWidth: 2, // same width selected or not, so the card doesn't shift when you switch
    borderColor: colors.hairline,
    padding: spacing.md,
    gap: spacing.xs,
    ...shadow.card,
  },
  selected: { borderColor: colors.brand, backgroundColor: colors.brandTint },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  label: { ...type.headline, color: colors.text },
  sample: { width: 36, height: 0, marginVertical: spacing.xs },
  sampleSolid: { borderTopWidth: 4, borderTopColor: colors.routeLower, borderRadius: 2 },
  sampleDashed: { borderTopWidth: 3, borderTopColor: colors.routeFast, borderStyle: "dashed" },
  time: { ...type.sectionTitle, color: colors.text },
  distance: { ...type.body, color: colors.textMuted },
  spots: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    marginTop: spacing.xs,
    alignSelf: "flex-start",
    borderRadius: shape.pill,
    paddingVertical: 3,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.hairline,
  },
  spotsWarn: { backgroundColor: colors.errorBg },
  spotsText: { ...type.caption, color: colors.text, flexShrink: 1 },
});
