import { Ionicons } from "@expo/vector-icons";
import { Redirect, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { PageDots } from "@/components/PageDots";
import { OnboardingScreen } from "@/components/OnboardingScreen";
import { PrimaryButton } from "@/components/PrimaryButton";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

const ILLUSTRATION_HEIGHT = 190;

/**
 * A tiny picture of the idea: a street grid, a red high-risk street, and a blue lower-risk route that goes
 * around it from home to school. Built from plain Views, sized in percentages so it fits any phone width.
 */
function Illustration() {
  return (
    <View style={styles.map} accessible accessibilityLabel={strings.welcome.illustrationLabel}>
      {/* the street grid */}
      {[32, 80, 140].map((top) => (
        <View key={`h${top}`} style={[styles.street, { top, left: 0, right: 0, height: 12 }]} />
      ))}
      {(["13%", "40%", "66%", "88%"] as const).map((left) => (
        <View key={`v${left}`} style={[styles.street, { left, top: 0, bottom: 0, width: 12 }]} />
      ))}
      {/* the high-risk street (red) along the middle road */}
      <View style={[styles.line, styles.red]} />
      {/* the lower-risk route (blue) around it */}
      <View style={[styles.line, styles.blueDownLeft]} />
      <View style={[styles.line, styles.blueAcross]} />
      <View style={[styles.line, styles.blueUpRight]} />
      {/* home and school */}
      <View style={styles.home} />
      <View style={styles.school}>
        <Ionicons name="school" size={18} color={colors.onBrand} />
      </View>
    </View>
  );
}

export default function Welcome() {
  const router = useRouter();
  const onboarded = useAppStore((state) => state.onboarded);
  if (onboarded) return <Redirect href="/" />;

  return (
    <OnboardingScreen
      footer={
        <>
          <PageDots count={3} index={0} />
          <PrimaryButton title={strings.welcome.next} onPress={() => router.push("/onboarding/promise")} />
        </>
      }
    >
      <Text style={styles.eyebrow}>{strings.appName}</Text>
      <Illustration />
      <Text style={styles.title} accessibilityRole="header">
        {strings.welcome.title}
      </Text>
      <View style={styles.rows}>
        {strings.welcome.rows.map((row) => (
          <View key={row.text} style={styles.row}>
            <View style={styles.disc}>
              <Ionicons name={row.icon} size={24} color={colors.brand} />
            </View>
            <Text style={styles.rowText}>{row.text}</Text>
          </View>
        ))}
      </View>
    </OnboardingScreen>
  );
}

const styles = StyleSheet.create({
  eyebrow: { ...type.eyebrow, color: colors.brandDark, marginTop: spacing.sm },
  map: {
    height: ILLUSTRATION_HEIGHT,
    borderRadius: 24,
    backgroundColor: colors.brandSoft,
    overflow: "hidden",
    ...shadow.card,
  },
  street: { position: "absolute", backgroundColor: colors.surface },
  line: { position: "absolute", borderRadius: 4 },
  red: { backgroundColor: colors.riskHigh, left: "13%", width: "75%", top: 82, height: 8 },
  blueDownLeft: { backgroundColor: colors.routeLower, left: "13%", marginLeft: 3, width: 6, top: 86, height: 60 },
  blueAcross: { backgroundColor: colors.routeLower, left: "13%", marginLeft: 3, width: "75%", top: 143, height: 6 },
  blueUpRight: { backgroundColor: colors.routeLower, left: "88%", marginLeft: 3, width: 6, top: 86, height: 63 },
  home: {
    position: "absolute",
    left: "13%",
    marginLeft: -2,
    top: 78,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.text,
    borderWidth: 3,
    borderColor: colors.surface,
  },
  school: {
    position: "absolute",
    left: "88%",
    marginLeft: -12,
    top: 68,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brand,
    borderWidth: 3,
    borderColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { ...type.screenTitle, color: colors.text, marginTop: spacing.sm },
  rows: { gap: spacing.sm },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    padding: spacing.md,
    ...shadow.card,
  },
  disc: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  rowText: { ...type.body, color: colors.text, flex: 1 },
});
