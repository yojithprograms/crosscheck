import { Ionicons } from "@expo/vector-icons";
import { Redirect, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { OnboardingScreen } from "@/components/OnboardingScreen";
import { PageDots } from "@/components/PageDots";
import { PrimaryButton } from "@/components/PrimaryButton";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

/** A tiny picture of the idea: a red high-risk street and a blue lower-risk route that goes around it. */
function Illustration() {
  return (
    <View style={styles.map} accessible accessibilityLabel={strings.welcome.illustrationLabel}>
      <View style={[styles.line, styles.red]} />
      <View style={[styles.line, styles.blueUp]} />
      <View style={[styles.line, styles.blueAcross]} />
      <View style={[styles.line, styles.blueDown]} />
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
      <Illustration />
      <Text style={styles.title} accessibilityRole="header">
        {strings.welcome.title}
      </Text>
      <View style={styles.rows}>
        {strings.welcome.rows.map((row) => (
          <View key={row.text} style={styles.row}>
            <Ionicons name={row.icon} size={28} color={colors.brand} />
            <Text style={styles.rowText}>{row.text}</Text>
          </View>
        ))}
      </View>
    </OnboardingScreen>
  );
}

const styles = StyleSheet.create({
  map: {
    height: 150,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
    marginTop: spacing.md,
  },
  line: { position: "absolute", borderRadius: 4 },
  red: { backgroundColor: colors.riskHigh, height: 8, width: 230, top: 70, left: 20, transform: [{ rotate: "-8deg" }] },
  blueUp: { backgroundColor: colors.routeLower, width: 6, height: 56, left: 56, top: 40 },
  blueAcross: { backgroundColor: colors.routeLower, height: 6, width: 190, left: 56, top: 38 },
  blueDown: { backgroundColor: colors.routeLower, width: 6, height: 56, left: 240, top: 38 },
  title: { ...type.screenTitle, color: colors.text },
  rows: { gap: spacing.lg },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  rowText: { ...type.body, color: colors.text, flex: 1 },
});
