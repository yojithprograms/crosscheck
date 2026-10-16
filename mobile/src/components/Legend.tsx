import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

function Swatch({ kind }: { kind: "high" | "medium" | "crash" | "report" }) {
  if (kind === "high") return <View style={[styles.line, { backgroundColor: colors.riskHigh, height: 5 }]} />;
  if (kind === "medium") {
    return <View style={[styles.line, styles.dashed, { borderColor: colors.riskMedium }]} />;
  }
  if (kind === "crash") return <View style={[styles.dot, { backgroundColor: colors.crash }]} />;
  return (
    <View style={[styles.dot, { backgroundColor: colors.report }]}>
      <Text style={styles.bang}>!</Text>
    </View>
  );
}

/** What the lines and dots on the map mean, plus the (i) button that opens "How risk scores work". */
export function Legend() {
  const router = useRouter();
  const items = [
    { kind: "high", label: strings.map.legend.high },
    { kind: "medium", label: strings.map.legend.medium },
    { kind: "crash", label: strings.map.legend.crash },
    { kind: "report", label: strings.map.legend.report },
  ] as const;
  return (
    <View style={styles.card}>
      {items.map((item) => (
        <View key={item.kind} style={styles.item}>
          <View style={styles.swatch}>
            <Swatch kind={item.kind} />
          </View>
          <Text style={styles.label}>{item.label}</Text>
        </View>
      ))}
      <Pressable
        onPress={() => router.push("/how-it-works")}
        accessibilityRole="button"
        accessibilityLabel={strings.map.howScoresWork}
        style={styles.info}
        hitSlop={8}
      >
        <Ionicons name="information-circle" size={26} color={colors.brand} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    gap: spacing.xs,
    ...shadow.floating,
  },
  item: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  swatch: { width: 28, alignItems: "center" },
  label: { ...type.caption, color: colors.text },
  line: { width: 26, height: 4, borderRadius: 2 },
  dashed: { height: 0, borderTopWidth: 3, borderStyle: "dashed", backgroundColor: "transparent" },
  dot: { width: 14, height: 14, borderRadius: 7, alignItems: "center", justifyContent: "center" },
  bang: { color: "white", fontSize: 10, fontWeight: "700", lineHeight: 12 },
  info: { alignSelf: "flex-start", minWidth: shape.minTouchTarget, minHeight: shape.minTouchTarget, justifyContent: "center", alignItems: "center", marginTop: 2 },
});
