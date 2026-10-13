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

/** A centered message for errors, empty lists, and screens that are still coming. */
export function EmptyState({ icon, title, body, action }: Props) {
  return (
    <View style={styles.wrap}>
      <Ionicons name={icon} size={48} color={colors.textMuted} />
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      <Text style={styles.body}>{body}</Text>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: shape.screenPadding * 2, gap: spacing.md },
  title: { ...type.sectionTitle, color: colors.text, textAlign: "center" },
  body: { ...type.body, color: colors.textMuted, textAlign: "center" },
});
