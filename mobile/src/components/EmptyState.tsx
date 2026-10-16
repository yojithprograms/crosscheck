import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps, ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = {
  icon: ComponentProps<typeof Ionicons>["name"];
  title: string;
  body: string;
  action?: ReactNode;
};

/** A centered message for errors, empty lists, and screens that are still coming: a big icon in a soft blue disc. */
export function EmptyState({ icon, title, body, action }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.halo}>
        <View style={styles.disc}>
          <Ionicons name={icon} size={44} color={colors.brand} />
        </View>
      </View>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      <Text style={styles.body}>{body}</Text>
      {action ? <View style={styles.action}>{action}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: shape.screenPadding * 1.5, gap: spacing.md },
  // Two rings of pastel blue behind the icon give it a gentle glow.
  halo: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: colors.brandTint,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.sm,
  },
  disc: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { ...type.sectionTitle, color: colors.text, textAlign: "center" },
  body: { ...type.body, color: colors.textMuted, textAlign: "center", maxWidth: 320 },
  action: { alignSelf: "stretch", marginTop: spacing.sm },
});
