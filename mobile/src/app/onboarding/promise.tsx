import { Ionicons } from "@expo/vector-icons";
import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { ChipGroup } from "@/components/Chip";
import { OnboardingScreen } from "@/components/OnboardingScreen";
import { PageDots } from "@/components/PageDots";
import { PrimaryButton } from "@/components/PrimaryButton";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Age = "under13" | "13plus";

// Both answers look exactly the same and neither is pre-selected (DESIGN.md §10.1). Don't reorder or restyle one.
const AGE_OPTIONS: { value: Age; label: string }[] = [
  { value: "under13", label: strings.promise.ageUnder13 },
  { value: "13plus", label: strings.promise.age13Plus },
];

/** One promise: an icon in a pale blue disc, a heading, and a short paragraph. */
function InfoCard({ icon, title, body }: { icon: "lock-closed" | "shield-checkmark" | "sparkles"; title: string; body: string }) {
  return (
    <Card>
      <View style={styles.cardRow}>
        <View style={styles.disc}>
          <Ionicons name={icon} size={22} color={colors.brand} />
        </View>
        <View style={styles.cardTexts}>
          <Text style={styles.cardTitle}>{title}</Text>
          <Text style={styles.cardBody}>{body}</Text>
        </View>
      </View>
    </Card>
  );
}

export default function BeforeYouStart() {
  const router = useRouter();
  const onboarded = useAppStore((state) => state.onboarded);
  const setAgeGate = useAppStore((state) => state.setAgeGate);
  const [age, setAge] = useState<Age | null>(null);
  if (onboarded) return <Redirect href="/" />;

  const onUnderstand = () => {
    if (age === "13plus") {
      setAgeGate("ok");
      router.push("/onboarding/school");
    } else if (age === "under13") {
      setAgeGate("under13"); // the app now shows the ask-an-adult message, now and every time it opens
    }
  };

  return (
    <OnboardingScreen
      footer={
        <>
          <PageDots count={3} index={1} />
          <PrimaryButton title={strings.promise.understand} onPress={onUnderstand} disabled={age === null} />
        </>
      }
    >
      <Text style={styles.title} accessibilityRole="header">
        {strings.promise.title}
      </Text>
      <InfoCard icon="lock-closed" title={strings.promise.privacyTitle} body={strings.promise.privacy} />
      <InfoCard icon="shield-checkmark" title={strings.promise.safetyTitle} body={strings.promise.safety} />
      <InfoCard icon="sparkles" title={strings.promise.aiTitle} body={strings.promise.ai} />
      <View style={styles.age}>
        <Text style={styles.cardTitle}>{strings.promise.ageQuestion}</Text>
        <ChipGroup options={AGE_OPTIONS} value={age} onChange={setAge} />
      </View>
    </OnboardingScreen>
  );
}

const styles = StyleSheet.create({
  title: { ...type.screenTitle, color: colors.text },
  cardRow: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  disc: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  cardTexts: { flex: 1, gap: spacing.xs },
  cardTitle: { ...type.headline, color: colors.text },
  cardBody: { ...type.body, color: colors.textMuted },
  age: { gap: spacing.md, marginTop: spacing.sm },
});
