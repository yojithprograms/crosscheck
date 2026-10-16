import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, StyleSheet, Text, TextInput, View } from "react-native";

import { useSchools } from "@/api/hooks";
import type { School } from "@/api/types";
import { EmptyState } from "@/components/EmptyState";
import { OnboardingScreen } from "@/components/OnboardingScreen";
import { PageDots } from "@/components/PageDots";
import { PressableScale } from "@/components/PressableScale";
import { PrimaryButton } from "@/components/PrimaryButton";
import { strings } from "@/copy/strings";
import { useAppStore } from "@/state/store";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

function SchoolRow({ school, selected, onPress }: { school: School; selected: boolean; onPress: () => void }) {
  return (
    <PressableScale
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      style={[styles.row, selected && styles.rowSelected]}
      scaleTo={0.98}
    >
      <View style={styles.rowText}>
        <Text style={styles.schoolName}>{school.name}</Text>
        <View style={styles.levelChip}>
          <Text style={styles.levelText}>{strings.schoolPicker.levels[school.level]}</Text>
        </View>
      </View>
      <Ionicons
        name={selected ? "checkmark-circle" : "ellipse-outline"}
        size={26}
        color={selected ? colors.brand : colors.border}
      />
    </PressableScale>
  );
}

/** S3: pick your school. Opened from Settings (?from=settings) the button says Save and goes back. */
export default function ChooseSchool() {
  const router = useRouter();
  const { from } = useLocalSearchParams<{ from?: string }>();
  const fromSettings = from === "settings";

  const savedSchoolId = useAppStore((state) => state.schoolId);
  const setSchool = useAppStore((state) => state.setSchool);
  const completeOnboarding = useAppStore((state) => state.completeOnboarding);

  const schools = useSchools();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<string | null>(fromSettings ? savedSchoolId : null);

  const matches = (schools.data ?? []).filter((s) => s.name.toLowerCase().includes(query.trim().toLowerCase()));

  const onContinue = () => {
    if (!picked) return;
    setSchool(picked);
    if (fromSettings) {
      router.back();
    } else {
      completeOnboarding();
      router.replace("/");
    }
  };

  let content;
  if (schools.isPending) {
    content = (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand} />
        <Text style={styles.muted}>{strings.schoolPicker.loading}</Text>
      </View>
    );
  } else if (schools.isError) {
    content = (
      <EmptyState
        icon="cloud-offline-outline"
        title={strings.schoolPicker.unreachableTitle}
        body={strings.schoolPicker.unreachableBody}
        action={<PrimaryButton title={strings.schoolPicker.tryAgain} onPress={() => void schools.refetch()} />}
      />
    );
  } else {
    content = (
      <>
        <View style={styles.list} accessibilityRole="radiogroup">
          {matches.map((school) => (
            <SchoolRow key={school.id} school={school} selected={school.id === picked} onPress={() => setPicked(school.id)} />
          ))}
          {matches.length === 0 ? <Text style={styles.muted}>{strings.schoolPicker.noMatches}</Text> : null}
        </View>
        <Text style={styles.muted}>{strings.schoolPicker.coverage(schools.data.length)}</Text>
      </>
    );
  }

  return (
    <OnboardingScreen
      footer={
        <>
          {fromSettings ? null : <PageDots count={3} index={2} />}
          <PrimaryButton
            title={fromSettings ? strings.schoolPicker.save : strings.schoolPicker.continue}
            onPress={onContinue}
            disabled={!picked}
          />
        </>
      }
    >
      <Text style={styles.title} accessibilityRole="header">
        {strings.schoolPicker.title}
      </Text>
      <View style={styles.searchBox}>
        <Ionicons name="search" size={20} color={colors.textMuted} />
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder={strings.schoolPicker.searchPlaceholder}
          accessibilityLabel={strings.schoolPicker.searchLabel}
          placeholderTextColor={colors.textMuted}
          autoCorrect={false}
          style={styles.search}
        />
      </View>
      {content}
    </OnboardingScreen>
  );
}

const styles = StyleSheet.create({
  title: { ...type.screenTitle, color: colors.text },
  searchBox: {
    height: shape.buttonHeight,
    borderRadius: shape.cardRadius,
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    ...shadow.card,
  },
  search: { flex: 1, height: shape.buttonHeight, ...type.body, color: colors.text },
  list: { gap: spacing.md },
  row: {
    minHeight: 68,
    borderRadius: shape.cardRadius,
    borderWidth: 2,
    borderColor: colors.hairline,
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
    ...shadow.card,
  },
  rowSelected: { borderColor: colors.brand, backgroundColor: colors.brandTint },
  rowText: { flex: 1, gap: spacing.xs, alignItems: "flex-start" },
  schoolName: { ...type.headline, color: colors.text },
  levelChip: { backgroundColor: colors.brandSoft, borderRadius: shape.pill, paddingHorizontal: spacing.sm + 2, paddingVertical: 2 },
  levelText: { ...type.caption, fontWeight: "600", color: colors.brandDark },
  muted: { ...type.caption, color: colors.textMuted },
  center: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xl },
});
