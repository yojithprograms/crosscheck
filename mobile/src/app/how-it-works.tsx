import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { useMeta } from "@/api/hooks";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

function Section({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.section}>
      <View style={styles.accent} />
      <Text style={styles.sectionTitle} accessibilityRole="header">
        {title}
      </Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
}

/** S19 · five short sections, written for students. Numbers come from GET /meta. */
export default function HowItWorks() {
  const meta = useMeta();
  const t = strings.howItWorks;
  const [colorsSection, looksAtSection] = t.sections;
  const capture = meta.data ? Math.round(meta.data.metrics.full_top10_capture * 100) : null;

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Section {...colorsSection} />
      <Section {...looksAtSection} />
      {meta.isPending ? <ActivityIndicator color={colors.brand} accessibilityLabel={t.loading} /> : null}
      {meta.isError ? <Text style={styles.body}>{t.loadError}</Text> : null}
      {meta.data && capture !== null ? (
        <>
          <Section title={t.testedTitle} body={t.tested(capture)} />
          <Section title={t.routesTitle} body={t.routes} />
          <Section title={t.limitsTitle} body={t.limits(meta.data.data_through)} />
        </>
      ) : (
        <Section title={t.routesTitle} body={t.routes} />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: shape.screenPadding, gap: spacing.lg, backgroundColor: colors.bg },
  section: {
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: shape.cardRadius,
    padding: spacing.lg,
    ...shadow.card,
  },
  accent: { width: 32, height: 4, borderRadius: 2, backgroundColor: colors.brand },
  sectionTitle: { ...type.sectionTitle, color: colors.text },
  body: { ...type.body, color: colors.text },
});
